import json
import os
from data_magic import *
simulationsData = []
mypath = './new_test'
files = [os.path.join(mypath, f) for f in os.listdir(mypath) if
         os.path.isfile(os.path.join(mypath, f)) if f.startswith('output')]

summa = {}
log = open('logger.log', 'a')
for x in files:
    s = '--------------' + x + '----------------\n'
    log.write(s)
    summa.update(file_parser(x, log))

with open('alpha.json', 'w') as f:
    json.dump(summa, f)
