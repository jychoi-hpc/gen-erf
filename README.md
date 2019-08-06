Wrapper command for running staging application
===============================================

This is an utility to write Explicit Resource File (ERF) file.

Installation
------------

`gen-erf.py` is a single python file. You can simply download as follows:

```
$ wget https://raw.githubusercontent.com/jychoi-hpc/gen-erf/master/gen-erf.py && chmod +x gen-erf.py
```


Example
-------

1. XGC1-XGCa coupling

```
$ ./gen-erf.py 0,3,0,3:"xgc1":"-g" 21,3,0,3:"xgc1":"-g" 9,4,0,3:"xgca" 30,4,0,3:"xgca" 
```
