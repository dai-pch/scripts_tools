#!/bin/bash
# echo in runone
work_dir=`pwd`
# echo workdir is $work_dir
script_name=$(basename $1)
script_name=${script_name%%.*}

# echo script name is $script_name
if [ ! -e $script_name ]; then
mkdir $script_name
fi
cd $script_name

function complete() {
    cp $work_dir/$script_name/m5out/stats.txt $work_dir/result/$script_name.txt 
    cp $work_dir/$script_name/run.log $work_dir/log/$script_name.log 
    cd $work_dir
    exit 0
}

if [[ -f "run.log" ]]; then
    run_log_end=$(tail -n 1 run.log)
    if [[ ${run_log_end} =~ "Exiting @ tick " ]]; then
        echo Skip ${work_dir}/$1 since it already have results.
        complete
        exit 0
    fi
fi

echo run ${work_dir}/$1
# $work_dir/$1 2>&1 |tee run.log
complete

