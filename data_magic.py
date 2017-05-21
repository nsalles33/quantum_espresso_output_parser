import re
import hashlib
from parser import *


def line():
    print('----------------------')


def debug(simulations, id_s):
    for y in simulations[id_s]:
        print(y)
        print(simulations[id_s][y])
        line()


def file_parser(file, log=None):
    """
    file: name of the file as string
    log: TextIOWrapper
    output: dict with data (see README)
    """
    if log is None:
        # if I put it as log default parameter the file is
        # always created
        log = open('{}_parser.log'.format(file), 'a')
    textfile = open(file, 'r')
    filetext = textfile.read()
    if len(re.findall(r_close, filetext)) == 1:
        log.write('job eneded correctly\n')
    elif len(re.findall(r_close, filetext)) == 0:
        log.write('job ended uncorrectly\n')
    else:
        log.write('wut?? THIS FILE IS NOT MENT TO BE PARSED\n')
        # TODO raise an error wold be better
        return {}

    # how many energies are in the file?
    # 1 energy => 1 simulation.
    # 0 energy => no simulation.
    # 1+ energies => error.
    matches = [x for x in re.findall(scf_data_out['r_total_energy'], filetext,
                                     re.MULTILINE)]
    if len(matches) != 0:
        n_simulations = len(matches)
        log.write('{} simulations found\n'.format(n_simulations))
    else:
        log.write('no energy found very bad!!!!\n')
        # TODO raise an error wold be better
        return {}

    # simulation initialization:
    simulations = {}

    if_bfgs, split_text = find_bfgs(filetext)

    if if_bfgs:
        for i, v in enumerate(split_text):
            kind, text = v
            simulation = {}
            valid_simulation = True
            damage_simulation = False
            if kind == 'scf':
                try:
                    simulation.update(scf_complete(text))
                except CorruptedData as e:
                    log.write(str(e) + '\n')
                    if 'total_energy' in e.parsed_data:
                        log.write('energy recovered')
                        simulation.update(e.parsed_data)
                        simulation['damage'] = True
                        damage_simulation = True
                    else:
                        valid_simulation = False
            elif kind == 'bfgs':
                try:
                    simulation.update(bfgs_complete(text))
                except CorruptedData as e:
                    log.write(str(e) + '\n')
                    if 'total_energy' in e.parsed_data:
                        log.write('energy recovered')
                        simulation.update(e.parsed_data)
                        simulation['damage'] = True
                        damage_simulation = True
                    else:
                        valid_simulation = False
            else:
                raise ValueError('kind not implemented')

            # be careful: key here is the key of the previous simulation!
            if not valid_simulation:
                for k, v in simulations.items():
                    v['last'] = key
                break

            # i = 0 does not have a previous key
            if i > 0:
                previous_key = key

            key = hashlib.sha224(text.encode('utf-8')).hexdigest()

            # key manager among the simulation
            if i == 0:
                simulations[key] = dict(file=str(file),
                                        firts=key,
                                        number=(i, len(split_text) - 1))
                simulations[key].update(simulation)
                first_key = key
            elif (i == len(split_text) - 1) or damage_simulation:
                simulations[previous_key]['next'] = key
                for k, v in simulations.items():
                    v['last'] = key
                simulations[key] = dict(file=str(file),
                                        first=first_key,
                                        number=(i, len(split_text) - 1),
                                        previous=previous_key,
                                        last=key)
                simulations[key].update(simulation)
                break
            else:
                simulations[key] = dict(file=str(file),
                                        first=first_key,
                                        number=(i, len(split_text) - 1),
                                        previous=previous_key)
                simulations[key].update(simulation)
                simulations[previous_key]['next'] = key

    else:
        log.write('no bfgs calculation founded\n')
        kind, text = split_text[0]
        key = hashlib.sha224(text.encode('utf-8')).hexdigest()
        simulations[key] = dict(file=str(file),
                                firts=key,
                                last=key,
                                number=(0, 0))
        try:
            simulations[key].update(scf_complete(text))
        except CorruptedData as e:
            log.write(str(e) + '\n')
            if 'total_energy' in e.parsed_data:
                log.write('energy recovered')
                simulation.update(e.parsed_data)
                simulation['damage'] = True
    textfile.close()
    debug(simulations, id_simulations[0])
    return simulations
