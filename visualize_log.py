from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import matplotlib as mpl
from datetime import datetime
import time
import argparse
import seaborn as sns
import pandas as pd

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize Ping Log")
    parser.add_argument("--log", type=str, default="ping.log", help="Log file")
    parser.add_argument("--ssh", type=str, help="If set, use SSH to download log file from the specified host")
    parser.add_argument("--live", action="store_true", help="Live plot")
    parser.add_argument("--window", type=float, help="Show only last <window> seconds of data")
    parser.add_argument("--interval", type=float, default=10, help="Interval in seconds for live plot")
    parser.add_argument("--violin", action="store_true", help="Show also violin plot")
    args = parser.parse_args()

    running = True

    fig = plt.figure()
    if args.live:
        plt.ion()
        def on_close(event):
            plt.ioff()
            global running
            running = False
            
        fig.canvas.mpl_connect('close_event', on_close)

    if args.ssh:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        username, hostname = args.ssh.split('@')
        port = 22 if ':' not in hostname else int(hostname.split(':')[1])
        hostname = hostname.split(':')[0]
        ssh.connect(hostname, port, username)
        sftp = ssh.open_sftp()
        
    while running:
        if args.ssh:
            with sftp.open(args.log) as f:
                lines = f.readlines()
        else:
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
            
        axs: list[plt.Axes] | plt.Axes = fig.subplots(1, 2 if args.violin else 1, sharey='row')    
        if not args.violin:
            axs: list[plt.Axes] = [axs]
        cmap = {}
        for host_id, (host, data) in enumerate(hosts.items()):
            timestamps = data["timestamps"]
            values = data["values"]
            timeouts = data["timeouts"]
            errors = data["errors"]
            color = mpl.colormaps["rainbow"](host_id / len(hosts))
            cmap[host] = color
            axs[0].grid(True)
            axs[0].plot(timestamps, values, label=f"{host}", color=color)
            axs[0].set_xlabel('Time')
            axs[0].set_ylabel('Ping (ms)')
            axs[0].set_title('Ping Log')
            axs[0].xaxis.set_major_formatter(mdates.DateFormatter('%b %d %H:%M:%S'))
            axs[0].xaxis.set_major_locator(plt.MaxNLocator('auto'))
            fig.autofmt_xdate()
            for i, timeout in enumerate(timeouts):
                axs[0].axvline(x=timeout, color=color, linestyle='--', label=f"{host} timeout" if i == 0 else None)
            for i, error in enumerate(errors):
                axs[0].axvline(x=error, color=color, linestyle=':', label=f"{host} error" if i == 0 else None)

        axs[0].legend()
        
        if args.violin:
            df = pd.DataFrame(columns=['host', 'timestamp', 'value'])
            for host, data in hosts.items():
                for timestamp, value in zip(data["timestamps"], data["values"]):
                    df.loc[len(df)] = [host, timestamp, value]
            sns.violinplot(ax=axs[1], x='host', y='value', data=df, scale='width', hue='host', cut=0, inner='quartile', palette=cmap)
            
        plt.tight_layout()
        if args.live:
            plt.draw()
            plt.pause(args.interval)
            plt.clf()
        else:
            plt.show()
            break
    if args.ssh:
        sftp.close()
        ssh.close()