#!python3

import argparse
import json
import re
import os
import os.path as path
import sys
from openpyxl import Workbook
from common_script import load_cfg, Executor, proc_meta
from tree import Tree


def parse_contents(src, items_cfg, executor):
    res = {}
    for idx, item_cfg in enumerate(items_cfg):
        reg = item_cfg["regex"]
        search_iter = re.finditer(reg, src)
        for search_res in search_iter:
            item_name = item_cfg["name"]
            item_value = item_cfg["value"]
            executor.set_var("match", search_res.groups())
            item_name = executor.proc_embd_str(item_name)
            item_value = executor.proc_embd_str(item_value)
            # print(item_name)
            # print(item_value)
            res[item_name] = item_value
    return res

def parse_name(regex, name):
    # regex = "cpu(\d+)-(LRU|T)_SWAP(-mram)?-(sp2k.+).txt$"
    sr = re.match(regex, name)
    if sr is None:
        raise ValueError('File name error.')
    return sr

def parse_file(file_path, cfg, executor, res=dict()):
    f_dir, f_name = path.split(file_path)
    name_match = parse_name(cfg["file_name"], f_name)
    if not name_match:
        return res
    executor.set_var("file_name_match", name_match.groups())
    f = open(file_path, 'r')
    c = parse_contents(f.read(), cfg["items"], executor)
    f.close()
    # save
    dic = res
    for hier in cfg["hierachy"]:
        hier_a = executor.proc_embd_str(hier)
        dic.setdefault(hier_a, dict())
        dic = dic[hier_a] 
    dic.update(c)
    # print(dic)
    # print(res)
    return res

def parse_folder(folder_path, cfg, executor, res=dict()):
    for root, dirs, files in os.walk(folder_path):
        for f in files:
            f_path = path.join(root, f)
            try:
                res = parse_file(f_path, cfg, executor, res)
            except ValueError as e:
                continue
    res = Tree.from_dict(res)
    return res

def data_proc(data):
    base_line_cls = 'LRU_NUCA'
    for bench_dist in data.values():
        for cls_dist in bench_dist.values():
            base_line = cls_dist[base_line_cls]
            ipcs = filter(lambda x: re.search('ipc|miss_rate', x[0]) is not None, base_line.items())
            for cls, stats_dict in cls_dist.items():
                if cls == base_line_cls:
                    for key, _ in ipcs:
                        stats_dict[key + '_normal'] = 1.0
                else:
                    for key, base in ipcs:
                        stats_dict[key + '_normal'] = float(stats_dict[key]) / float(base)
    return data

def dic_depth(dic):
    # print(dic)
    n = 0
    c = dic
    while True:
        if isinstance(c, dict) and len(c) > 0:
            n += 1
            c = list(dic.values())[0]
            dic = c
        else:
            break
    return n

def trav_dict(dic, n, call_back, default_str=""):
    items = [(default_str, dic)]
    for depth in range(n):
        items_n = []
        for name, dic in items:
            for k, v in dic.items():
                items_n.append(("-".join(filter(lambda x: x != "", [name, k])), v))
        items = items_n
    res = []
    for name, v in items:
        r = call_back(name, v)
        res.append(r)
    return res

def depth_trav_dict(root, max_depth=-1, leaf_func=None, pre_func=None, post_func=None):
    # print("travdict: ", root)
    # print("depth: ", max_depth)
    if pre_func:
        pre_func(root)
    if (max_depth == 0 or not isinstance(root, dict)): # leaf
        if leaf_func:
            leaf_func(root, max_depth)
        if post_func:
            post_func(root, max_depth)
    else:
        for k, v in root.items():
            depth_trav_dict(v, max_depth-1, leaf_func, pre_func, post_func)
            if post_func:
                post_func(root, max_depth)

def gen_blk(v, row_n, ws):
    # scan col item
    col_items = v.get_next_n_nodes(v.get_level()-1)
    col_items = [n.name for _, n in col_items]
    # add col name
    col_items.sort()
    for idy, col_item in enumerate(col_items):
        ws.cell(row=idy+row_n+1, column=1).value = col_item
        
    # add blk
    gen_row_blk(v, row_n, 1, 2, col_items, ws)

def gen_row_blk(root, row_n, r_s, c_s, item_list, ws):
    # row header
    if row_n == 0: # leaf
        for node in root.get_children():
            idy = item_list.index(node.name)
            ws.cell(row=idy+r_s, column=c_s).value = node.data
        return 1
    # not leaf
    c_n = c_s
    items = list(root.get_children())
    items.sort(key=lambda x:x.name)
    for n in items:
        w = gen_row_blk(n, row_n-1, r_s+1, c_n, item_list, ws)
        ws.merge_cells(start_row=r_s, end_row=r_s, start_column=c_n, end_column=c_n+w-1)
        ws.cell(row=r_s, column=c_n).value = n.name
        c_n += w
    return c_n - c_s

def gen_ws(k, v, row_n, wb):
    ws = wb.create_sheet(title=k)
    gen_blk(v, row_n, ws)

def gen_wb(name, data, ws_n, row_n):
    wb = Workbook()
    ws_data = data.get_next_n_nodes(ws_n)
    wss = list(map(lambda tp: gen_ws("-".join([name] + tp[0]), tp[1], row_n, wb), ws_data))
    return (name, wb)

def gen_tb(data, d_name, wb_n=0, ws_n=1):
    # print(dic_depth(data))
    data.root.name = d_name
    col_n = 1
    assert(col_n + wb_n + ws_n <= data.tree_depth())
    row_n = data.tree_depth() - col_n - wb_n - ws_n - 1
    wb_data = data.root.get_next_n_nodes(wb_n)
    wbs = list(map(lambda tp: gen_wb("-".join([d_name] + tp[0]), tp[1], ws_n, row_n), wb_data))
    return wbs

def write_tbs(tbs, folder):
    for name, tb in tbs:
        tb.save(path.join(folder, name + ".xlsx"))

def get_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', type=str)
    parser.add_argument('-L', '--config-path', type=list)
    parser.add_argument('-c', '--config', type=str, default="parser.cfg")
    parser.add_argument('-o', '--default-name', type=str, default="result")
    parser.add_argument('--run-begin', default="<%")
    parser.add_argument('--run-end', default="%>")
    return parser

def run():
    parser = get_argparser()
    args = parser.parse_args()
    cfg = load_cfg(args.config, args.config_path)
    executor = Executor()
    proc_meta(args, cfg["meta"], executor)
    cfg = cfg["config"]
    data = parse_folder(args.dir, cfg, executor)
    # data = data_proc(data)
    xslx_cfg = cfg["xslx"]
    tbs = gen_tb(data, args.default_name, xslx_cfg["book"], xslx_cfg["sheet"])
    write_tbs(tbs, sys.argv[1])

if __name__ == "__main__":
    run()
    # print(res)

