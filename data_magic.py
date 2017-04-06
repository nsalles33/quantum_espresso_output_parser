import re
import uuid
from parser import *


def line():
    print('----------------------')


def debug(simulations, id_s):
    for y in simulations[id_s]:
        print(y)
        print(simulations[id_s][y])
        line()


def file_parser(file, log=None):
    if log == None:
        # if I put it as log default parameter the file is
        # always created
        log = open('file_parser.log', 'a')
    textfile = open(file, 'r')
    filetext = textfile.read()
    if len(re.findall(r_close, filetext)) == 1:
        log.write('job eneded correctly\n')
        anomalous_stop = False
    elif len(re.findall(r_close, filetext)) == 0:
        log.write('job ended uncorrectly\n')
        anomalous_stop = True
    else:
        log.write('wut??\n')
        exit()

    # scopro quante energie sono presenti nel fine
    # ad ogni energia corrisponde una simulazione.
    # questo l'ho deciso io, tutti gli altri dati sono "opzionali"
    matches = [x for x in re.findall(scf_data_out['r_total_energy'], filetext,
                                     re.MULTILINE)]
    if len(matches) != 0:
        n_simulations = len(matches)
        id_simulations = tuple([str(uuid.uuid4())
                                for x in range(len(matches))])
        log.write('{} simulations found\n'.format(n_simulations))
        first = id_simulations[0]
        last = id_simulations[-1]
    else:
        log.write('no energy found very bad!!!!\n')
        exit()

    # simulation inizialization:
    simulations = {}
    for i, x in enumerate(id_simulations):
        simulations[x] = {}
        simulations[x]['first'] = id_simulations[0]
        simulations[x]['last'] = id_simulations[-1]
        simulations[x]['number'] = (i + 1, n_simulations)
        if i != 0:
            simulations[x]['previous'] = id_simulations[i - 1]
        if i != n_simulations - 1:
            simulations[x]['next'] = id_simulations[i + 1]

    # carico i dati di bfgs -> passaggio necessario solo per bfgs:
    bfgs_data = {}
    bfgs_calculation = False
    for x in bfgs_set:
        data = re.findall(bfgs_set[x], filetext, re.MULTILINE)
        bfgs_data[x[2:]] = data
    if len(bfgs_data['start']) == 1:
        bfgs_calculation = True
        if len(bfgs_data['end']) == 1:
            log.write('the bfgs algorithm ended\n')
            bfgs_anomalous_stop = False
        else:
            log.write('the bfgs algorithm didn \'t end due to problems\n')
            bfgs_anomalous_stop = True
        if not bfgs_anomalous_stop:
            if len(bfgs_data['bfgs_not_converged']) == 0:
                scf_step, bfgs_step = bfgs_data['bfgs_converged'][0]
                scf_step = int(scf_step)
                bfgs_step = int(bfgs_step)
                simulations[last]['bfgs_converged'] = True
            else:
                bfgs_step = int(bfgs_data['nstep'])
                simulations[last]['bfgs_converged'] = False
            if len(bfgs_data['recalculation']) == 1:
                simulations[last]['recalculation'] = True
        else:
            try:
                scf_step_started = int(
                    re.findall(r'^ +number of scf cycles += +(\d+)', filetext,
                               re.MULTILINE)[-1])
                bfgs_step_started = int(
                    re.findall(r'^ +number of bfgs steps += +(\d+)', filetext,
                               re.MULTILINE)[-1])
            except IndexError:
                log.write('who cares, everything should work '
                          'anyway without this data\n')

    else:
        log.write('BFGS not present\n')

    if bfgs_calculation and not anomalous_stop:
        first_scf = filetext.split(bfgs_data['start'][0])[0]
        simulations[first] = complete_scf(first_scf)

        # recover of bfgs data
        bfgs_iterations_text, bfgs_last = filetext.split(bfgs_data['end'][0])
        bfgs_iterations_text = bfgs_iterations_text.split('number of '
                                                          'scf cycles')
        bfgs_iterations_text.pop(0)
        bfgs_iterations_text.append(bfgs_last)

        for i, j in enumerate(bfgs_iterations_text):
            simulations[id_simulations[i + 1]] = bfgs_complete(j)

    elif bfgs_calculation and anomalous_stop and \
            len(bfgs_data['end']) == 1:
        log.write('data corrupted this is bad\n')

        first_scf = filetext.split(bfgs_data['start'][0])[0]
        simulations[first] = complete_scf(first_scf)

        # recover of bfgs data
        bfgs_iterations_text, bfgs_last = filetext.split(bfgs_data['end'][0])
        bfgs_iterations_text = bfgs_iterations_text.split('number of '
                                                          'scf cycles')
        bfgs_iterations_text.pop(0)
        bfgs_iterations_text.append(bfgs_last)

        for i, j in enumerate(bfgs_iterations_text):
            try:
                simulations[id_simulations[i + 1]] = bfgs_complete(j)
            except CorruptedData as e:
                log.write(str(e))
                log.write('\n')
                simulations[id_simulations[i + 1]] = e.parsed_data
                simulations[id_simulations[i + 1]]['damage'] = True

    elif len(bfgs_data['start']) == 1 and anomalous_stop and \
            len(bfgs_data['end']) == 0:
        log.write('data corrupted this is bad^2\n')
        first_scf = filetext.split(bfgs_data['start'][0])[0]
        simulations[first] = complete_scf(first_scf)

        # recover of bfgs data
        bfgs_iterations_text = filetext.split('number of scf cycles')
        bfgs_iterations_text.pop(0)

        for i, j in enumerate(bfgs_iterations_text):
            try:
                simulations[id_simulations[i + 1]] = bfgs_complete(j)
            except CorruptedData as e:
                log.write(str(e) + '\n')
                if 'total_energy' in e.parsed_data:
                    log.write()
                    simulations[id_simulations[i + 1]] = e.parsed_data
                    simulations[id_simulations[i + 1]]['damage'] = True
                else:
                    # some data in the next step are available, like new
                    # atomic positions or something, but not the energy
                    # so we discard it
                    log.write(str(i) + '/' + str(len(id_simulations)) + '\n')
                    log.write(j)
                    simulations[id_simulations[i]]['damage_next'] = True

    elif anomalous_stop:
        log.write('data corrupted this is very unlucky\n')
        try:
            simulations[first] = complete_scf(filetext)
        except CorruptedData as e:
            log.write(str(e))
            log.write('\n')
            simulations[first] = e.parsed_data
            simulations[first]['damage'] = True

    textfile.close()
    debug(simulations, id_simulations[0])

    return simulations
