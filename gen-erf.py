#!/usr/bin/env python

import numpy as np
import argparse
import collections 

## Parameters
parser = argparse.ArgumentParser()
parser.add_argument('HYPERSLAB', help="hyperslab selection (offset,block[,stride,[count]]:command[:-g]])", nargs='+')
parser.add_argument('--nnodes', help='nnodes', type=int, default=1)
parser.add_argument('--cpu', help='cpu per resource set', type=int, default=1)
parser.add_argument('--smt', help='smt', type=int, default=1)
parser.add_argument('--ppn', help='ppn', type=int, default=42)
parser.add_argument('--outfile', help='outfile', default='erf_file')
args = parser.parse_args()

## Read current nodes
nnodes = args.nnodes
ppn = args.ppn
nproc = nnodes*ppn
smt = args.smt
print ('NNODES:', nnodes)
print ('SMT:', smt)

## hyperselect: offset,block,stride,count
## offset + (block+stride)*(count-1) + block <= dim
## Example:
## _ X X _ _ _ X X _ _
## _ X X _ _ _ X X _ _
## _ X X _ _ _ X X _ _
## _ _ _ _ _ _ _ _ _ _
## _ X X _ _ _ X X _ _
## _ X X _ _ _ X X _ _
## _ X X _ _ _ X X _ _
## _ _ _ _ _ _ _ _ _ _
##
## Data size: {8,10}
##    Offset: {0, 1}
##     Block: {3, 2}
##     Count: {2, 2}
##    Stride: {1, 3}

def process_single(exp):
    exp.split(',')
    tk = exp.split(',')
    offset = int(tk[0])
    block = 1
    stride = 0
    count = 1
    if len(tk) > 1:
        block = int(tk[1])
    if len(tk) > 2:
        stride = int(tk[2])
    if len(tk) > 3:
        count = int(tk[3])
    
    lst = list()
    for i in range(count):
        lst.append(tuple((offset, offset+block)))
        offset += (block+stride)
    
    return (lst)

def process(exp):
    tk = exp.split(' ')
    lst = list()
    if len(tk) > 1:
        one = list()
        for item in tk:
            for x in process_single(item):
                one.append(x)
        lst.append(one)
    else:
        for x in process_single(exp):
            lst.append([x,])
    return (lst)

def range2str(rx, smt):
    s = '{'
    n = len(rx)
    for i, x in enumerate(rx):
        r0 = x[0]*smt 
        r1 = x[1]*smt-1
        if r1 > r0:
            s += '%d-%d'%(r0, r1)
        else:
            s += '%d'%r0
        if i<n-1:
            s += ','
    s += '}'
    return s

m0index = 0
m1index = 0
def mem2str(rx):
    global m0index
    global m1index
    s = '{'
    n = len(rx)
    for i, x in enumerate(rx):
        r0 = x[0]
        r1 = x[1]
        if (r0>20):
            s += '%d-%d'%(m1index*1000+309663, m1index*1000+309663+1000/n-1)
            m1index += 1
        else:
            s += '%d-%d'%(m0index*1000, m0index*1000+1000/n-1)
            m0index += 1
            assert r1<22, "Cannot cross memory domain: %d,%d"%(r0, r1)
        if i<n-1:
            s += ','
    s += '}'
    return s

cpus = []
lst = []
app = []
gpu = []
for i, exp in enumerate(args.HYPERSLAB):
    tk = exp.split(':')
    exp = tk[0]

    nm = 'app%d'%(i)
    g = 0
    if len(tk) > 1:
        nm = tk[1]
    if len(tk) > 2:
        if tk[2] == '-g': g = 1

    for x in process(exp):
        lst.append(x)
        app.append(nm)
        gpu.append(g)

## Verbose
print("Selected:")
for i, (rx, nm, g) in enumerate(zip(lst, app, gpu)):
    print(i, rx, nm, g)
print("")

## Check any duplication
dset = set()
for x in lst:
    for r0, r1 in x:
        xs = set(range(r0, r1))
        ys = dset.intersection(xs)
        assert len(ys)==0, "Duplicated: %s"%(ys)
        dset.update(xs)

cmd = list(collections.OrderedDict.fromkeys(app))

f = open(args.outfile, "w")
for i, cmdline in enumerate(cmd):
    f.write("app %d: %s\n"%(i, cmdline))

f.write("cpu_index_using: logical\n")
f.write("overlapping-rs: warn\n")
f.write("oversubscribe_cpu: warn\n")
f.write("oversubscribe_gpu: allow\n")
f.write("oversubscribe_mem: allow\n")
f.write("launch_distribution: packed\n")

gid = 0
rank = 0
for n in range(nnodes):
    for i, (rx, nm, g) in enumerate(zip(lst, app, gpu)):
        if g == 1:
            f.write("rank: %d: { host: %d; cpu: %s ; gpu: {%d} ; mem: %s } : app %d\n"%(rank, n+1, range2str(rx, smt), gid, mem2str(rx), cmd.index(nm)))
            gid += 1
        else:
            f.write("rank: %d: { host: %d; cpu: %s ; mem: %s } : app %d\n"%(rank, n+1, range2str(rx, smt), mem2str(rx), cmd.index(nm)))
        rank += 1
    gid = 0
    m0index = 0
    m1index = 0
f.close()

print ('Saved:', args.outfile)
print ("Done.")
