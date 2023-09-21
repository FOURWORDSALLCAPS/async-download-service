import argparse
import asyncio
import aiofiles
import logging

from aiohttp import web


logger = logging.getLogger(__name__)


async def create_zip_archive(directory, delay, photo_path):
    zip_bytes = b''

    try:
        process = await asyncio.create_subprocess_shell(
            f"cd {photo_path} && zip -r -j - {directory}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True,
        )

        while True:
            chunk = await process.stdout.read(500 * 1024)
            if not chunk:
                break
            if delay:
                await asyncio.sleep(delay)
            zip_bytes += chunk
            logger.debug(f"Sending archive chunk ...")

    except (asyncio.CancelledError, Exception):
        logger.debug(f"Download was interrupted")
        await complete_archiving()

    return zip_bytes


async def complete_archiving():
    pid_command = await asyncio.create_subprocess_exec(
        'pgrep', 'zip',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await pid_command.communicate()
    pid_output = stdout.decode("utf-8")
    pids = pid_output.strip().split("\n")
    for pid in pids:
        kill_command = await asyncio.create_subprocess_exec('kill', '-9', pid)
        await kill_command.communicate()


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


async def archive_and_stream(request, delay, photo_path):
    archive_hash = request.match_info.get('archive_hash')

    if archive_hash == '7kna':
        zip_bytes = await create_zip_archive('7kna', delay, photo_path)
    elif archive_hash == 'rur2':
        zip_bytes = await create_zip_archive('rur2', delay, photo_path)
    else:
        raise web.HTTPNotFound(text='Архив не существует или был удален')

    response = web.StreamResponse()
    response.headers['Content-Type'] = 'application/zip'
    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    await response.prepare(request)

    await response.write(zip_bytes)
    return response


def main():
    parser = argparse.ArgumentParser(description='Архивация и потоковая передачи архивов')
    parser.add_argument('--elog', action='store_true', help='Включить логирование')
    parser.add_argument('--delay', type=float, default=None, help='Замедление скачивание в секундах')
    parser.add_argument('--photo_path', default='test_photos', help='Путь к каталогу с фото')
    args = parser.parse_args()
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', lambda request: archive_and_stream(request, args.delay, args.photo_path)),
    ])
    if args.elog:
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')

    web.run_app(app)


if __name__ == '__main__':
    main()
