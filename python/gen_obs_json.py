#!/usr/bin/env python3

import datetime as dt
import sys
import json
import numpy as np
import matplotlib.dates as dates
import matplotlib.pyplot as plt

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body
from astropy.time import Time
# Silence astropy download logs
from astropy.utils.data import conf
conf.remote_timeout = 30
conf.show_progress_bar = False

AZ_MIN, AZ_MAX = 29, 355 #
ALT_MIN, ALT_MAX = 15, 84 #
ONDREJOV = EarthLocation(lat=49.9085742*u.deg, lon=14.7797511*u.deg, height=512*u.m) #

def resolve_target(name, time):
    solar_system_names = ['sun', 'moon', 'mars', 'jupiter', 'saturn', 'venus']
    if name.lower() in solar_system_names:
        return get_body(name, time, ONDREJOV) #
    try:
        return SkyCoord.from_name('PSR ' + name, parse=False) #
    except:
        try:
            return SkyCoord.from_name(name, parse=True) #
        except:
            return None

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: script.py YYYY.MM.DD Target1,Target2..."}))
        return

    date_str = sys.argv[1]
    targets = sys.argv[2].split(',')
    start_dt = dt.datetime.strptime(date_str, "%Y.%m.%d")
    obs_time = Time(start_dt)

    # 1-minute steps for 24 hours (1441 points)
    delta_t = np.linspace(0, 24, 24*60+1) * u.hour
    times = obs_time + delta_t
    plot_times = [start_dt + dt.timedelta(minutes=i) for i in range(len(delta_t))]

    output_data = {}
    plt.figure(figsize=(10, 6))

    for i, name in enumerate(targets):
        name = name.strip()
        target = resolve_target(name, obs_time)
        if not target:
            output_data[name] = "Not found"
            continue

        altaz = target.transform_to(AltAz(obstime=times, location=ONDREJOV))
        visible = (altaz.az.value > AZ_MIN) & (altaz.az.value < AZ_MAX) & \
                  (altaz.alt.value > ALT_MIN) & (altaz.alt.value < ALT_MAX)

        plt.fill_between(plot_times, i, i+0.8, where=visible, alpha=0.3, label=name)

        # Logical window extraction
        windows = []
        is_on = False
        start_w = None
        
        for t_idx, is_vis in enumerate(visible):
            if is_vis and not is_on:
                is_on = True
                start_w = plot_times[t_idx]
            elif not is_vis and is_on:
                is_on = False
                windows.append([start_w, plot_times[t_idx]])
        
        if is_on:
            windows.append([start_w, plot_times[-1]])

        # Merge overnight windows (connect end-of-day to start-of-day)
        if len(windows) > 1:
            first = windows[0]
            last = windows[-1]
            # If visible at 00:00 and 23:59, merge them
            if visible[0] and visible[-1]:
                merged_start = last[0].strftime("%H:%M")
                merged_end = first[1].strftime("%H:%M")
                # Remove the split parts and add the merged one
                formatted = [f"{w[0].strftime('%H:%M')} - {w[1].strftime('%H:%M')}" for w in windows[1:-1]]
                formatted.append(f"{merged_start} - {merged_end}")
                output_data[name] = formatted
            else:
                output_data[name] = [f"{w[0].strftime('%H:%M')} - {w[1].strftime('%H:%M')}" for w in windows]
        else:
            output_data[name] = [f"{w[0].strftime('%H:%M')} - {w[1].strftime('%H:%M')}" for w in windows] if windows else "No visibility"

    plt.gca().xaxis.set_major_formatter(dates.DateFormatter('%H:%M'))
    plt.yticks(range(len(targets)), targets)
    plt.grid(True, alpha=0.2)
    plt.title(f"Visibility at Ondrejov: {date_str}")
    
    img_name = f"plan_{date_str.replace('.','')}.png"
    plt.savefig(img_name, dpi=100)
    plt.close()

    print(json.dumps({"image": img_name, "windows": output_data}))

if __name__ == "__main__":
    main()