
import argparse
import os, stat
import sys
import json


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
        # print(self.path_list)
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

    def proc_embd_str(self, pre_str, run_begin="<%", run_end="%>"):
        split_begin = pre_str.split(run_begin, 1)
        if len(split_begin) == 2:
            head = split_begin[0]
            tail = split_begin[1]
            split_end = tail.split(run_end, 1)
            script = split_end[0]
            tail = split_end[1]
            run_res = self.evaluate_indep(script)
            if isinstance(run_res, str):
                value = head + run_res + tail
            else:
                raise Exception("Error: unexcepted return value: " + str(run_res) + ". Need str.")
            return self.proc_embd_str(value)
        else:
            return pre_str


def load_cfg(file_name, folders):
    cfg_paths = []
    if folders:
        cfg_paths = folders
    # working directory
    cfg_paths.append(os.getcwd())
    # this python file path
    cfg_paths.append(sys.path[0])
    cfg_loader = FileLoader(cfg_paths)
    cfg_str = cfg_loader(file_name)
    cfg_str = cfg_str.replace('\r', '').replace('\n', '')
    cfg = json.loads(cfg_str)
    return cfg

def proc_meta(args, cfg_meta, executor):
    if not cfg_meta:
        return
    if cfg_meta["context"]:
        context = cfg_meta["context"]
        executor.execute(context)


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

