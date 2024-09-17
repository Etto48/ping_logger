from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import matplotlib as mpl
from datetime import datetime
import time
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize Ping Log")
    parser.add_argument("--log", type=str, default="ping.log", help="Log file")
    parser.add_argument("--live", action="store_true", help="Live plot")
    parser.add_argument("--window", type=float, help="Show only last <window> seconds of data")
    parser.add_argument("--interval", type=float, default=10, help="Interval in seconds for live plot")
    args = parser.parse_args()

    running = True

    if args.live:
        plt.ion()
        fig = plt.figure()
        def on_close(event):
            plt.ioff()
            global running
            running = False
            
        fig.canvas.mpl_connect('close_event', on_close)

    while running:
        with open(args.log) as f:
            lines = f.readlines()
        
        hosts = {}

        time_format = '%a %b %d %H:%M:%S %Y'

        for line in lines:
            # line format: [Mon Sep 20 15:00:00 2021] <host>: <event_text>
            start_time = time.time()
            date_start = 1
            date_end = line.index(']', date_start)
            timestamp = line[date_start:date_end]
            timestamp = time.strptime(timestamp, time_format)
            seconds = time.mktime(timestamp)
            dt = datetime.fromtimestamp(seconds)

            if args.window:
                if start_time > seconds + args.window:
                    continue

            host = line[date_end + 2:line.index(':', date_end)]
            
            if host not in hosts:
                hosts[host] = {
                    "timestamps": [],
                    "values": [],
                    "timeouts": [],
                    "errors": []
                }
            hosts[host]["timestamps"].append(dt)
            
            event_start = line.index(':', date_end) + 2
            event_text = line[event_start:].strip()
            if event_text == 'Timeout' or event_text == 'Error':
                hosts[host]["values"].append(None)
                match event_text:
                    case 'Timeout':
                        hosts[host]["timeouts"].append(dt)
                    case 'Error':
                        hosts[host]["errors"].append(dt)
            else:
                ms_value, ms_unit = event_text.split()
                assert ms_unit == 'ms'
                hosts[host]["values"].append(float(ms_value))
                
        for host_id, (host, data) in enumerate(hosts.items()):
            timestamps = data["timestamps"]
            values = data["values"]
            timeouts = data["timeouts"]
            errors = data["errors"]
            color = mpl.colormaps["rainbow"](host_id / len(hosts))
            
            plt.plot(timestamps, values, label=f"{host}", color=color)
            plt.xlabel('Time')
            plt.ylabel('Ping (ms)')
            plt.title('Ping Log')
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%b %d %H:%M:%S'))
            plt.gca().xaxis.set_major_locator(plt.MaxNLocator(10))
            plt.gcf().autofmt_xdate()
            for i, timeout in enumerate(timeouts):
                plt.axvline(x=timeout, color=color, linestyle='--', label=f"{host} timeout" if i == 0 else None)
            for i, error in enumerate(errors):
                plt.axvline(x=error, color=color, linestyle=':', label=f"{host} error" if i == 0 else None)

        plt.legend()
        plt.tight_layout()
        if args.live:
            plt.draw()
            plt.pause(args.interval)
            plt.clf()
        else:
            plt.show()
            break
