#!/bin/sh -x
j=1
while [ $j -lt 11 ]; do
    i=3
    while [ $i -lt 12 ]; do
        log=$(python3.8 main.py $i)
        cd results
        python3.8 analysis.py "$log" $i | tee -a analysis$i.csv
        cd ..
        i=$(( $i + 2 ))
    done
    j=$(( $j + 1))
done
