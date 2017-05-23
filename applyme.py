import json
import os
import logging
from data_magic import *

logging.basicConfig(filename='./parse.log', level=logging.INFO)

simulationsData = []
mypath = './new_test'
files = [os.path.join(mypath, f) for f in os.listdir(mypath) if
         os.path.isfile(os.path.join(mypath, f)) if f.startswith('output')]

summa = {}
for x in files:
    logging.info('--------------' + x + '----------------')
    summa.update(file_parser(x))

with open('v0.2.1.json', 'w') as f:
    json.dump(summa, f)
