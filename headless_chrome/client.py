import subprocess, json, asyncio, logging, pprint, base64, tempfile, random
import websockets, requests

DEFAULT_CHROME = '/usr/bin/google-chrome'
BASE_TIMEOUT = 90.0
SLEEP_BEFORE_NAV = 8

class Client:
    def __init__(self, exec_path, headless=True):
        if exec_path is None:
            exec_path = DEFAULT_CHROME
        self.path = exec_path
        self.loop = asyncio.get_event_loop()
        self.command_id = 0
        self.headless = headless
        self.tablist = []
        self.network_events = []
        self.user_data_dir = tempfile.TemporaryDirectory()
        self.port = random.choice(range(10000, 50000))

    def start(self):
        args = [self.path,
                '--remote-debugging-port={}'.format(self.port),
                '--window-size=1280,1696',
                '--no-first-run',
                '--user-data-dir={}'.format(self.user_data_dir.name)]
        if self.headless:
            args += ['--headless', '--disable-gpu']
        self.process = subprocess.Popen(args, stderr=subprocess.DEVNULL)
        logging.debug('Chrome args: {}'.format(self.process.args))

    def _find_tabs(self):
        response = requests.get('http://localhost:{}/json'.format(self.port))
        self.tablist = json.loads(response.text)

    def _get_tab_debugger_url(self):
        if len(self.tablist) == 0:
            self._find_tabs()
        tab = next((t for t in self.tablist if t['type'] == 'page'), None)
        if tab is None or 'webSocketDebuggerUrl' not in tab:
            self._find_tabs()
            tab = next((t for t in self.tablist if t['type'] == 'page'), None)
            if tab is None or 'webSocketDebuggerUrl' not in tab:
                logging.error('debugger url not found')
                pprint.pprint(self.tablist)
                pprint.pprint(tab)
        return tab['webSocketDebuggerUrl']

    def cleanup(self):
        self.process.terminate()
        try:
            self.user_data_dir.cleanup()
        except Exception:
            pass

    def _get_cid(self):
        cid = self.command_id
        self.command_id += 1
        return cid

    async def __aenter__(self):
        self.start()
        await asyncio.sleep(SLEEP_BEFORE_NAV)
        self.websocket = await websockets.connect(
                self._get_tab_debugger_url(), max_size=None)
        return self

    async def __aexit__(self, *exc):
        await self.websocket.close()
        self.cleanup()
        return False

    async def _listen_for_cid(self, cid):
        while True:
            resp = await self.websocket.recv()
            resp = json.loads(resp)
            if 'id' in resp and resp['id'] == cid:
                return resp

    async def _listen_for_event(self, event):
        while True:
            resp = await self.websocket.recv()
            resp = json.loads(resp)
            if 'method' in resp and resp['method'] == event:
                return resp

    # Just generate the command id and coroutine.
    def _get_debug_command(self, method, params={}):
        cid = self._get_cid()
        send = self.websocket.send(json.dumps({
            "id": cid,
            "method": method,
            "params": params
            }))
        return (cid, send)

    async def _send_debug_command(self, method, params={}):
        cid, send = self._get_debug_command(method, params)
        return await send

    async def _wait_on_debug_command(self, method, params={}):
        cid, send = self._get_debug_command(method, params)
        await send
        return await asyncio.ensure_future(self._listen_for_cid(cid))

    async def send_network_enable(self):
        return await self._wait_on_debug_command('Network.enable')

    async def send_network_disable(self):
        return await self._wait_on_debug_command('Network.disable')

    async def send_page_enable(self):
        return await self._wait_on_debug_command('Page.enable')

    async def send_page_disable(self):
        return await self._wait_on_debug_command('Page.disable')

    async def take_screenshot(self):
        resp = await self._wait_on_debug_command('Page.captureScreenshot')
        return base64.b64decode(resp['result']['data'])

    async def send_page_navigate(self, url):
        await self._send_debug_command('Page.navigate', { "url": url })

    async def record_navigation(self, url):
        logging.info('Opening "{}"'.format(url))
        self.network_events = []
        await self.send_page_navigate(url)
        while True:
            resp = json.loads(await self.websocket.recv())
            if 'method' not in resp:
                continue
            if resp['method'].startswith('Network'):
                self.network_events.append(resp)
            if resp['method'] == 'Page.loadEventFired':
                logging.debug('Load event fired for "{}"'.format(url))
                return
            if (resp['method'] == 'Network.loadingFailed' and
                    resp['params']['type'] == 'Document' and
                    resp['params']['requestId'].endswith('.1')):
                logging.debug('Document loading failed for "{}"'.format(url))
                return

async def record_navigation(url, chrome_path=DEFAULT_CHROME, headless=True,
        timeout=BASE_TIMEOUT, sleep=None):
    if sleep:
        await asyncio.sleep(sleep)

    async with Client(chrome_path, headless) as b:
        await b.send_network_enable()
        await b.send_page_enable()
        try:
            await asyncio.wait_for(b.record_navigation(url), timeout=timeout)
        except asyncio.TimeoutError:
            return { 'network_events': b.network_events, 'screenshot': None,
                    'timed_out': True }
        screenshot = await b.take_screenshot()
        return { 'network_events': b.network_events, 'screenshot': screenshot,
                'timed_out': False }
