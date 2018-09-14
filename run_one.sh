#/bin/bash
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
$work_dir/$1 2>&1 |tee run.log
cp $work_dir/$script_name/m5out/stats.txt $work_dir/result/$script_name.txt 
cp $work_dir/$script_name/run.log $work_dir/log/$script_name.log 
cd $work_dir

