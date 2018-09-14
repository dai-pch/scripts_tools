#/bin/bash
run_one () {
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
    # echo run ${work_dir}/$1
    source $work_dir/$1 2>&1 |tee run.log
    cp $work_dir/$script_name/m5out/stats.txt $work_dir/result/$script_name.txt 
    cp $work_dir/$script_name/run.log $work_dir/log/$script_name.log 
    cd $work_dir
}

if [ -z $1 ]; then
    echo Usage:
    echo $(basename $0) script_dir [process_number=8]
    exit
fi
script_dir=$1
script_dir=${script_dir%/*}
if [ -z $2 ]; then
    max_proc=8
else
    max_proc=$2
fi
self_dir=$(cd $(dirname $0); pwd)
echo $script_dir

files=`ls $script_dir`
echo $files
# make dir for result
rm -rf result
rm -rf log
mkdir result 
mkdir log 

echo $files | xargs -d ' ' -P $max_proc -I {} $self_dir/run_one.sh "${script_dir}/{}"
# for script in $files ;
# do
#     echo ${script_dir}${script}
#     # echo call runone.
#     run_one "${script_dir}${script}" &
# done
# wait
echo Done.

