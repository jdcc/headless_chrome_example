import argparse, asyncio, logging, subprocess, time, os.path

from client import record_navigation

def parse_args():
    parser = argparse.ArgumentParser(description="Visits a web page in headless chrome")
    parser.add_argument('url', help='URL to visit')
    parser.add_argument('--urls', help='File containing URLs to test (one per line)')
    parser.add_argument('--vpn', nargs='+', help='OpenVPN config file')
    parser.add_argument('--vpnauth', help='OpenVPN user credentials file')
    return parser.parse_args()

def sanitize_url(url):
    table = str.maketrans({ '/': '', ':': '_', ' ': '-', '.': '_' })
    return url.translate(table)

def setup_vpn(config, auth):
    vpn = subprocess.Popen(['sudo', 'openvpn', '--config', config, '--auth-user-pass', auth])
    time.sleep(4)
    return vpn

def teardown_vpn(vpn):
    subprocess.run(['sudo', 'killall', 'openvpn'])

def visit(url):
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(record_navigation(url))
    loop.run_until_complete(future)
    return future.result()

def get_filename(url, vpnconfig):
    if vpnconfig:
        return 'results/{}-{}.png'.format(sanitize_url(os.path.basename(vpnconfig)),
                sanitize_url(url))
    return 'results/{}.png'.format(sanitize_url(url))

def run(url, vpnconfig=None, vpnauth=None):
    vpn = None
    if vpnconfig:
        vpn = setup_vpn(vpnconfig, vpnauth)

    results = visit(url)
    if results['screenshot']:
        with open(get_filename(url, vpnconfig), 'wb') as f:
            f.write(results['screenshot'])

    if vpn:
        teardown_vpn(vpn)

def main():
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('websockets.protocol').setLevel(logging.WARNING)
    vpns = None
    urls = [args.url]
    if args.vpn:
        vpns = [args.vpn]
        if isinstance(args.vpn, list):
            vpns = args.vpn
    if args.urls:
        with open(args.urls) as f:
            urls = f.readlines()
    if vpns:
        for vpn in vpns:
            for url in urls:
                run(url.strip(), vpn, args.vpnauth)
    else:
        for url in urls:
            run(url.strip())
