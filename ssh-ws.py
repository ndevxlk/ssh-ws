import asyncio
import signal
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
BUFLEN = 65536
TARGET_HOST = '127.0.0.1'
TARGET_PORT = 22
LISTEN_HOST = '127.0.0.1'
LISTEN_PORT = 3000
MAX_BACKLOG = 1024
RESPONSE = b'HTTP/1.1 101 Switching Protocols\r\n\r\n'
async def pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter):
    try:
        while True:
            data = await src.read(BUFLEN)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except Exception:
        pass
    finally:
        try:
            dst.close()
            await dst.wait_closed()
        except Exception:
            pass
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        target_reader, target_writer = await asyncio.open_connection(
            TARGET_HOST, TARGET_PORT, limit=BUFLEN
        )
    except Exception:
        writer.close()
        await writer.wait_closed()
        return
    writer.write(RESPONSE)
    await writer.drain()
    await asyncio.gather(
        pipe(reader, target_writer),
        pipe(target_reader, writer),
        return_exceptions=True
    )
async def main():
    server = await asyncio.start_server(
        handle_client,
        LISTEN_HOST, LISTEN_PORT,
        reuse_address=True,
        reuse_port=True,
        backlog=MAX_BACKLOG,
        limit=BUFLEN
    )
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    async with server:
        await stop_event.wait()
        server.close()
        await server.wait_closed()
if __name__ == '__main__':
    asyncio.run(main())