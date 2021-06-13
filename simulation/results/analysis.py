import os
import sys
import pandas as pd
import numpy as np

dir_path = os.path.dirname(os.path.realpath(__file__)) 

for root, dirs, files in os.walk(dir_path): 
    tpt = sys.argv[1]
    tpt = tpt[:-11] + "Throughput.log"
    for f in files:  
        if f.endswith('.log'): 
            if f == sys.argv[1]:
                df = pd.read_csv(f)
                arr = df[df.columns[1]].to_numpy()
                print(np.amin(arr), np.percentile(arr, 25), np.median(arr), np.percentile(arr, 75), np.amax(arr), np.mean(arr), sep=", ")
            elif f == tpt:
                df = pd.read_csv(f)
                arr = df.to_numpy()
                xmax, ymax = arr.max(axis=0)
                xmax += 1
                a = {}
                for i in range(len(arr)):
                    if arr[i][0] in a.keys():
                        a[arr[i][0]] += 1
                    else:
                        a[arr[i][0]] = 1
                s = 0
                for k in a:
                    a[k] /= ymax
                    s += a[k]
                avg = s / xmax
                log = "tpt" + str(sys.argv[2]) + ".csv"
                fr = open(log, "a")
                fr.write(f"avg total acc all receivers, {s},  no of packs per timeslot per receiver, {avg}, xmax, {xmax}, ymax, {ymax}\n")
                fr.close()
