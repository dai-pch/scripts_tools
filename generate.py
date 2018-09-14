#!python3

import argparse
from copy import deepcopy
from jinja2 import Environment, FileSystemLoader, Template
import random
import os, stat
import sys
import json
from itertools import product


class FileLoader(object):
    def __init__(self, path=None):
        self.path_list = []
        self.add_path(path)

    def add_path(self, path):
        if isinstance(path, list):
            for p in path:
                self._add_path(p)
        elif isinstance(path, str):
            self._add_path(path)

    def _add_path(self, path):
        self.path_list.append(path)

    def __call__(self, filename):
        if self.path_list:
            for path in self.path_list:
                filepath = os.path.join(path, filename)
                if os.path.isfile(filepath):
                    f = open(filepath)
                    c = f.read()
                    f.close()
                    return c
            raise Exception("File " + filename + " not found.")
        else:
            raise Exception("No path specific for search file" + filename)


class Executor(object):
    def __init__(self):
        self.global_vars = dict()

    def set_var(self, name, value):
        # print("set", name, "to", value)
        self.global_vars[name] = value

    def set_vars(self, var_dict):
        for name, value in var_dict.items():
            self.set_var(name, value)

    def evaluate_indep(self, src, local_vars=dict()):
        res = eval(src, self.global_vars, local_vars)
        return res

    def execute_indep(self, src, local_vars=dict()):
        exec(src, self.global_vars, local_vars)

    def execute(self, src):
        exec(src, self.global_vars)

    def evaluate(self, src):
        res = eval(src, self.global_vars)
        return res


def get_env(args):
    template_paths = []
    if args.template_path:
        template_path += args.template_path
    # working directory
    template_paths.append(os.getcwd())
    # this python file path
    template_paths.append(sys.path[0])
    tmp_loader = FileSystemLoader(template_paths)
    env = Environment(loader=tmp_loader)
    return env


def load_cfg(args):
    cfg_paths = []
    if args.config_path:
        cfg_paths += args.config_path
    # working directory
    cfg_paths.append(os.getcwd())
    # this python file path
    cfg_paths.append(sys.path[0])
    cfg_loader = FileLoader(cfg_paths)
    cfg_str = cfg_loader(args.config)
    cfg_str = cfg_str.replace('\r', '').replace('\n', '')
    cfg = json.loads(cfg_str)
    return cfg


def proc_meta(args, cfg_meta, executor):
    if cfg_meta["context"]:
        context = cfg_meta["context"]
        executor.execute(context)


def preproc_config(args, executor, pre_cfg_config):
    run_begin = args.run_begin
    run_end = args.run_end
    res = []
    for key, value in pre_cfg_config.items():
        if isinstance(value, str) and (value.find(run_begin) >= 0):
            # print("sub")
            cfg_configs = []
            split_begin = value.split(run_begin, 1)
            head = split_begin[0]
            tail = split_begin[1]
            run_res = []
            split_end = tail.split(run_end, 1)
            script = split_end[0]
            tail = split_end[1]
            run_res = executor.evaluate_indep(script)
            if isinstance(run_res, list):
                value_tmp = head + "{}" + tail
                for param in run_res:
                    value = value_tmp.format(param)
                    cfg_config = deepcopy(pre_cfg_config)
                    cfg_config[key] = value
                    sub_name = "-" + str(param)
                    cfg_configs.append((sub_name, cfg_config))
            else:
                if isinstance(run_res, int):
                    run_res = str(run_res)
                if isinstance(run_res, str):
                    value = head + run_res + tail
                    cfg_config = deepcopy(pre_cfg_config)
                    cfg_config[key] = value
                    cfg_configs.append(("", cfg_config))
                else:
                    raise Exception("Error: unexcepted return value: " + str(run_res) + ". Need either str or list.")
            for cfg_name, cfg_config in cfg_configs:
                recurs = preproc_config(args, executor, cfg_config)
                res += map(lambda x: (cfg_name + x[0], x[1]), recurs)
            return res
    return [("", pre_cfg_config)]


def generate_one_config(args, env, executor, cfg_name, pre_cfg_config):
    cfg_configs = preproc_config(args, executor, pre_cfg_config)
    template = env.get_template(args.template)
    res = []
    for cfg_subname, cfg_config in cfg_configs:
        sp_contents = template.render(**cfg_config)
        sp_name = cfg_name + cfg_subname
        res.append((sp_name, sp_contents))
    return res


def do_main(args):
    cfg = load_cfg(args)
    executor = Executor()
    proc_meta(args, cfg.get("meta", dict()), executor)
    env = get_env(args)
    cfg_common = cfg["common"]
    res = []
    for cfg_name, cfg_config in cfg["config"].items():
        cfg = deepcopy(cfg_common)
        cfg.update(cfg_config)
        executor.set_vars(cfg)
        sps = generate_one_config(args, env, executor, cfg_name, cfg)
        res += sps
    return res


def get_cmd(is_sp2k, is_mram, benchs, tag):
    template = env.from_string(cmd_template)
    cmd = template.render( is_sp2k=is_sp2k, is_mram=is_mram, cpu_num=len(benchs), benchs=benchs, tag=tag )
    return cmd


def write_script(spdir, sps):
    for sp_name , sp_contents in sps:
        sp_path = os.path.join(spdir, sp_name + '.sh') 
        f = open(sp_path, 'w')
        f.write(sp_contents)
        f.close()
        os.chmod(sp_path, int(0o754))


def get_argparser():
    parser = argparse.ArgumentParser(description="Script generator.")
    parser.add_argument('dest_folder', type=str)
    parser.add_argument('-t','--template', type=str, default="script.template")
    parser.add_argument('-c','--config', type=str, default="config.json")
    parser.add_argument('-L','--config-path', type=list)
    parser.add_argument('-I','--template-path', type=list)
    parser.add_argument('--run-begin', default="<%")
    parser.add_argument('--run-end', default="%>")
    return parser


def test():
    cmd = get_cmd(is_sp2k=True, is_mram=True, benchs=sp2k6_benchs, tag='LRU')
    print(cmd)


def main():
    parser = get_argparser()
    args = parser.parse_args()
    res = do_main(args)
    write_script(args.dest_folder, res)

if __name__ == "__main__":
    main()
