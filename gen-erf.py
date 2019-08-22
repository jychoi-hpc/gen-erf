#!/usr/bin/env python

import numpy as np
import argparse
import collections
import logging
import sys
import random

def cmdlist(argv):
    '''
    return list of list
    '''
    cmds = list()
    _args = list()
    for x in argv:
        if x == ':':
            cmds.append(_args)
            _args = list()
        else:
            _args.append(x)

    cmds.append(_args)
    _args = list()

    return cmds

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
    if block+stride > 0:
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
            s += '%d-%d'%(m1index*1000+309664, m1index*1000+309664+1000/n-1)
            m1index += 1
        else:
            s += '%d-%d'%(m0index*1000, m0index*1000+1000/n-1)
            m0index += 1
            assert r1<22, "Cannot cross memory domain: %d,%d"%(r0, r1)
        if i<n-1:
            s += ','
    s += '}'
    return s

def main():
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    def usage():
        print ('USAGE: gen-erf.py <OPTIONS> <HYPERSLAB> [ : <HYPERSLAB> ]*')
        print ('====================')
        parser0.print_help()
        print ('--------------------')
        parser1.print_help()
        print ('--------------------')
        sys.exit()

    ## Parameters
    parser0 = argparse.ArgumentParser(prog='OPTIONS', add_help=False)
    parser0.add_argument('--cpu', help='cpu per resource set', type=int, default=1)
    parser0.add_argument('--smt', help='smt', type=int, default=1)
    parser0.add_argument('--ppn', help='ppn', type=int, default=42)
    parser0.add_argument('--outfile', help='outfile', default='erf_file')
    parser0.add_argument('--shuffle', help='shuffle', default=False, action='store_true')
    parser0.add_argument('--shufflerank', help='shufflerank', default=False, action='store_true')
    parser0.add_argument('--sortbyapp', help='sortbyapp', default=False, action='store_true')
    parser0.add_argument('--shufflebyapp', help='shufflebyapp', default=False, action='store_true')

    parser1 = argparse.ArgumentParser(prog='HYPERSLAB', add_help=False)
    parser1.add_argument('HYPERSLAB', help="hyperslab selection (offset,block[,stride,[count]]:command[:-g]])", nargs='+')
    parser1.add_argument('--nnodes', help='nnodes', type=int, default=1)

    cmds = cmdlist(sys.argv[1:])
    if len(cmds) < 1:
        usage()

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

    lst = []
    app = []
    gpu = []
    global m0index
    global m1index

    args, _unknown = parser0.parse_known_args(cmds[0])
    cmds[0] = _unknown

    ## Read current nodes
    ppn = args.ppn
    smt = args.smt
    outfile = args.outfile
    shuffle = args.shuffle
    shufflerank = args.shufflerank
    sortbyapp = args.sortbyapp
    shufflebyapp = args.shufflebyapp

    logging.debug ('PPN: %d' % ppn)
    logging.debug ('SMT: %d' % smt)

    item_all = []
    ntotal = 0
    m = 0
    for cmd in cmds:
        args, _unknown = parser1.parse_known_args(cmd)
        if len(_unknown) > 0:
            usage()
        nnodes = args.nnodes
        ntotal += nnodes

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
        logging.debug('Selected:')
        for i, (rx, nm, g) in enumerate(zip(lst, app, gpu)):
            logging.debug((i, rx, nm, g))

        ## Check any duplication
        dset = set()
        for x in lst:
            for r0, r1 in x:
                xs = set(range(r0, r1))
                ys = dset.intersection(xs)
                assert len(ys)==0, "Duplicated: %s"%(ys)
                dset.update(xs)

        item = []
        for nid in range(m, m+nnodes):
            gid = 0
            m0index = 0
            m1index = 0
            for i, (rx, nm, g) in enumerate(zip(lst, app, gpu)):
                item.append((rx, nm, g, nid, gid, mem2str(rx)))
                if g == 1:
                    gid += 1
        m += nnodes
        item_all.append(item)

    nodeindex=list(range(ntotal))
    if shuffle:
        random.shuffle(nodeindex)
    
    ax = np.array([ x[1] for item in item_all for x in item ])
    rankindex = np.arange(len(ax))

    apps = list(collections.OrderedDict.fromkeys(ax))

    if shufflerank:
        rankindex = np.random.permutation(len(ax))
        ax = ax[np.argsort(rankindex)]
    
    if shufflebyapp:
        p = None
        offset = 0
        for x in apps:
            n = len(ax[ax == x])
            if p is None:
                p = np.random.permutation(n)
            rankindex[ax == x] = p+offset
            offset += n
        ax = ax[np.argsort(rankindex)]

    if sortbyapp:
        aid = [ apps.index(x) for x in ax ]
        rankindex = rankindex[np.argsort(aid, kind='mergesort')]
        ax = ax[np.argsort(rankindex)]

    f = open(outfile, "w")
    for i, cmdline in enumerate(apps):
        f.write("app %d: %s\n"%(i, cmdline))

    f.write("cpu_index_using: logical\n")
    f.write("overlapping-rs: warn\n")
    f.write("oversubscribe_cpu: warn\n")
    f.write("oversubscribe_gpu: allow\n")
    f.write("oversubscribe_mem: allow\n")
    f.write("launch_distribution: packed\n")

    rank = 0
    for item in item_all:
        for rx, nm, g, n, gid, mx in item:
            #print (rx, nm, g, n, gid, mx)
            if g == 1:
                f.write("rank: %d: { host: %d; cpu: %s ; gpu: {%d} ; mem: %s } : app %d\n"\
                    %(rankindex[rank], nodeindex[n]+1, range2str(rx, smt), gid, mx, apps.index(nm)))
            else:
                f.write("rank: %d: { host: %d; cpu: %s ; mem: %s } : app %d\n"\
                    %(rankindex[rank], nodeindex[n]+1, range2str(rx, smt), mx, apps.index(nm)))

            rank += 1
    f.close()

    logging.info('Saved: %s' % outfile)
    logging.info('Done.')

if __name__ == '__main__':
    main()