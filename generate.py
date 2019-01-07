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
        template_paths += args.template_path
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
    key, value = None, None
    find_code = False
    for key_inter, value_inter in pre_cfg_config.items():
        if (isinstance(value_inter, str) and (value_inter.find(run_begin) >= 0)) or isinstance(value_inter, list):
            key = key_inter
            value = value_inter
            find_code = True
            break
    if not find_code:
        return [("", pre_cfg_config)]
    else:
        # process
        cfg_configs = []
        # exec
        if isinstance(value, str):
            # cut into 3 seg: head, script, tail
            split_begin = value.split(run_begin, 1)
            head = split_begin[0].lstrip()
            tail = split_begin[1].rstrip()
            run_res = []
            split_end = tail.split(run_end, 1)
            script = split_end[0]
            tail = split_end[1]
            # run
            run_res = executor.evaluate_indep(script)
            if isinstance(run_res, list):
                for param in run_res:
                    if head or tail:
                        value_tmp = head + "{}" + tail
                        value = value_tmp.format(param)
                    else:
                        value = param
                    cfg_config = deepcopy(pre_cfg_config)
                    cfg_config[key] = value
                    sub_name = "-" + str(param)
                    cfg_configs.append((sub_name, cfg_config))
            else:
                if head or tail:
                    value_tmp = head + "{}" + tail
                    value = value_tmp.format(run_res)
                else:
                    value = run_res
                pre_cfg_config[key] = value
                cfg_configs.append(('', pre_cfg_config))
        elif isinstance(run_res, list):
                for param in run_res:
                    cfg_config = deepcopy(pre_cfg_config)
                    cfg_config[key] = param
                    sub_name = "-" + str(param)
                    cfg_configs.append((sub_name, cfg_config))
        elif isinstance(run_res, int) or isinstance(run_res, float):
            raise Exception("Error: unexcepted control flow.")
        else:
            raise Exception("Error: unexcepted return value: " + str(run_res) + ". Need either str or list.")
        for cfg_name, cfg_config in cfg_configs:
            recurs = preproc_config(args, executor, cfg_config)
            res += map(lambda x: (cfg_name + x[0], x[1]), recurs)
        return res


def render(args, env, cfgs):
    template = env.get_template(args.template)
    res = []
    for name, cfg in cfgs:
        if cfg["_script_name"]:
            name = cfg["_script_name"]
        res.append((name, template.render(**cfg)))
    return res


def generate(args, executor, init, cfg_seq):
    cfg_gen = [init]
    # substitute cfg_seq into cfg_common sequencially
    for cfg_to_be_substituted in cfg_seq:
        cfg_gen_next = []
        for cfg_name, cfg in cfg_gen:
            executor.set_vars(cfg)
            cfg.update(cfg_to_be_substituted)
            cfg_gen_next += map(lambda x: (cfg_name + x[0], x[1]), preproc_config(args, executor, cfg))
        cfg_gen = cfg_gen_next
    return cfg_gen


def proc_cfgs(args, cfg, executor):
    cfg_common = cfg["common"]
    if isinstance(cfg_common, dict):
        cfg_common = [cfg_common]
    res = []
    for cfg_name, cfg_config in cfg["config"].items():
        if isinstance(cfg_config, dict):
            cfg_config = [cfg_config]
        cfgs = cfg_common + cfg_config + [{"_script_name": cfg.get("name")}]
        init_cfg = (cfg_name, {
            "_config_name": cfg_name
        })
        sps = generate(args, executor, init_cfg, cfgs)
        res += sps
    return res


def get_cmd(is_sp2k, is_mram, benchs, tag):
    template = env.from_string(cmd_template)
    cmd = template.render( is_sp2k=is_sp2k, is_mram=is_mram, cpu_num=len(benchs), benchs=benchs, tag=tag )
    return cmd


def write_script(spdir, sps):
    for sp_name, sp_contents in sps:
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
    
    cfg = load_cfg(args)
    executor = Executor()
    proc_meta(args, cfg.get("meta", dict()), executor)
    cfgs = proc_cfgs(args, cfg, executor)
    env = get_env(args)
    scripts = render(args, env, cfgs) 
    write_script(args.dest_folder, scripts)


if __name__ == "__main__":
    main()

