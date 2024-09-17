#!python3
from ping3 import ping
import argparse
import time
import regex as re

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ping Logger')
    parser.add_argument('--host', type=str, help='Host(s) to ping')
    parser.add_argument('--interval', '-i', type=float, default=10, help='Interval in seconds')
    parser.add_argument('--log', '-l', type=str, default='ping.log', help='Log file')
    parser.add_argument('--quiet', '-q', action='store_true', help='Quiet mode')
    parser.add_argument('--timeout', '-t', type=float, default=2, help='Timeout in seconds')
    args = parser.parse_args()

    hosts = args.host.split(',')

    while True:
        start_time = time.time()
        for host in hosts:
            result = ping(host, timeout=args.timeout)

            event_text = None
            match result:
                case None:
                    event_text = 'Timeout'
                case False:
                    event_text = 'Error'
                case v if isinstance(v, float):
                    event_text = f'{v*1000:.1f} ms'

            log_message = f'[{time.ctime()}] {host}: {event_text}'
            if not args.quiet:
                print(log_message)
            with open(args.log, 'a') as f:
                f.write(log_message + '\n')

        elapsed_time = time.time() - start_time
        time.sleep(max(0, args.interval - elapsed_time))
