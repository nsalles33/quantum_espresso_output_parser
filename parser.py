import re
import logging


class CorruptedData(Exception):
    def __init__(self, message, data, *args):
        super(CorruptedData, self).__init__(message)
        # clean the data form empty keys
        data_celaned = {k: v for k, v in data.items() if v != []}
        for x in args:
            data_celaned['{}_damage'.format(x)] = True
        self.parsed_data = data_celaned


class EnergyError(Exception):
    def __init__(self, message, data, *args):
        super(EnergyError, self).__init__(message)
        # clean the data form empty keys
        data_celaned = {k: v for k, v in data.items() if v != []}
        for x in args:
            data_celaned['{}_damage'.format(x)] = True
        self.parsed_data = data_celaned


# util to regexp
unit = r'((?:Ry|a\.?u\.?|(?:b|B)ohr|\/|(?:a|A)ng|kbar|g|cm|ev)+'\
       r'(?:\^|\*\*)?\d*)'
atoms_name = r'(?:C|H|O|N)'

# qe info
qe_info = dict(
    r_PWSCF_version=r'^ *Program PWSCF (.+) starts',
    )

# information of scf actually head informations
scf_input = dict(
    r_pseudopotential=r'^ *PseudoPot. # (\d+) for *(\w{1,2})'
                      r' *read from file:\n^ *(.+\.UPF)$',
    r_bli=r'^ *bravais-lattice index *= *(\d+)',
    r_alat=r'^ *lattice parameter \(alat\) *= *([\d\.\+\-]+) *{}'.format(unit),
    r_unit_cell_volume=r'^ *unit-cell volume *= *([\d\.\+\-]+) *{}'.format(
                       unit),
    r_cell_side_units=r'^ *crystal axes: \(cart. coord. in units of (alat)\)',
    r_cell_side=r' *a\((\d+)\) *= *\( *(-?[\d.]+) *(-?[\d.]+) *'
                '(-?[\d.]+) *\)',
    r_natoms=r'^ *number of atoms/cell *= *(\d+)',
    r_nspecies=r'^ *number of atomic types *= *(\d+)',
    r_dspecies=r'^ +(\w{1,2}) +(-?[\d.]+) +(-?[\d.]+)',
    r_nelectrons=r'^ *number of electrons *= *([\d\.\+\-]+)',
    r_nksstates=r'^ *number of Kohn-Sham states *= *(\d+)',
    r_cutoff=r'^ *kinetic-energy cutoff *= *([\d\.\+\-]+) *{}'.format(unit),
    r_charge_cutoff=r'^ *charge density cutoff *= *([\d\.\+\-]+) *{}'.format(
                    unit),
    r_threshold=r'^ *convergence threshold *= *(\d+.\d+E?-?\d*)',
    r_mixing=r'^ *mixing beta *= *([\d\.\+\-]+)')
scf_input_cryst = dict(
    r_cryst_split_begin=r'^ *Crystallographic axes',
    r_apos=r'^ +(\d+) +({})[^=]+= \( +([\d\+\-\.]+) +([\d\+\-\.]+) +'
           '([\d\+\-\.]+) +\)'.format(atoms_name),
    r_cryst_split_end=r'^ *Dense  grid')

# data of scf
# TODO, the pressure calculation is carried out in different way
# on different QE version
# here we have the most common version

scf_output = dict(
    r_total_energy=r'^![\w =]+([\d\.\+\- ]+){}'.format(unit),
    r_E_hartree=r'^ +hartree \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_onelectron=r'^ +one-electron \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_xc=r'^ +xc \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_ewald=r'^ +ewald \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_paw=r'^ +one-center paw \w+\. += +([\d\.\+\-]+) +{}'.format(unit),
    r_force_units=r'^ *Forces acting on atoms (cartesian axes, *{})'.
                  format(unit),
    r_force=r'atom +([\d\.\+\-]+) +type +([\d\.\+\-]+)'
            ' +force = +([\d\.\+\-]+) +([\d\.\+\-]+) +([\d\.\+\-]+)',
    r_stress_units=r' +total +stress +{}'.format(unit),
    r_pressure=r'\(kbar\) +P= +([\d\.\+\-]+)',
    r_stress_and_kbar_tensor=r'^ {2,3}([\d\.\+\-]+) +([\d\.\+\-]+) +'
                             r'([\d\.\+\-]+) {9,10}([\d\.\+\-]+) +'
                             r'([\d\.\+\-]+) +([\d\.\+\-]+)$')

# information of BFGS
# obs:
# * criteria are present only if the bfgs converged
# * nstep = maximimu nuber of step in BFGS
bfgs_set = dict(
    r_nstep=r'^ *nstep *= *(\d+)',
    r_start=r'^ +BFGS Geometry Optimization',
    r_bfgs_converged=r' +bfgs converged in +(\d+) +scf cycles and +(\d+) +'
                     'bfgs steps',
    r_bfgs_not_converged=r'^ +The maximum number of steps has been reached.',
    r_criteria=r'^ +\(criteria: +(energy) *< *([\d\.\+\-E]+) *{},'
               r' +(force) *< *([\d\.\+\-E]+) *{},'
               r' +(cell) *< *([\d\.\+\-E]+) *{} *\)'.format(unit, unit, unit),
    r_end=r'^ +End of BFGS Geometry Optimization',
    r_final_scf=r'^ *A final scf calculation at the relaxed structure',
    r_bfgs_split=r'number of scf cycles')

# data of bfgs:
bfgs_data_out = dict(
    r_scf_cycles=r'^ *number of scf cycles *= *(\d+)',
    r_bfgs_steps=r'^ *number of bfgs steps *= *(\d+)',
    r_unit_cell_volume=r'^ *new unit-cell volume *= *([\d\.\+\-]+) *{}'.format(
                       unit),
    r_cell_side_units=r'CELL_PARAMETERS \(([\w ]+= +[\d\.\+\-]+|bohr)\)',
    r_cell_side=r'^ {2,3}([\d\+\-\.]+) +([\d\+\-\.]+) +([\d\+\-\.]+)$',
    r_apos_units=r'ATOMIC_POSITIONS \((.+)\)',
    r_apos=r'^({}) +([\d\+\-\.]+) +([\d\+\-\.]+) +([\d\+\-\.]+)$'
                .format(atoms_name))

# closing string:
r_close = r'JOB DONE'


def find_bfgs(text, verbose=False):
    """
    given a full file check if it is a bfgs caluclation and if it is true
    it splits the text in a vector of single calculation
    output:
    if_bfgs, [('scf','text'),[ ('bfgs','text'),..]
    if verbose is True the ouput will contain extra info in a dict:
        bfgs_error = bool
        bfgs_converged = bool
        --- if bfgs_converged = True
        energy < value
        force < value
        cell < value
        -------------
        bfgs_final_scf = bool

    """
    bfgs_data = {}
    verbose_dict = {}
    for x in bfgs_set:
        data = re.findall(bfgs_set[x], text, re.MULTILINE)
        bfgs_data[x[2:]] = data

    # check if a BFGS calculation is present.
    if len(bfgs_data['start']) == 1:
        if_bfgs = True
    else:
        if_bfgs = False
        if verbose:
            return if_bfgs, [('scf', text)], verbose_dict
        else:
            return if_bfgs, [('scf', text)]

    # split the data in several calculation:
    split_data = []
    # first scf calculation
    tmp = re.split(bfgs_set['r_start'], text, flags=re.MULTILINE)
    split_data.append(('scf', tmp[0]))
    tmp = tmp[1]
    # final scf calculation
    if len(bfgs_data['final_scf']) == 1:
        tmp = re.split(bfgs_set['r_final_scf'], tmp, flags=re.MULTILINE)
        scf_last_text = tmp[1]
        # data for next step
        tmp = tmp[0]
    # final set of coordinate:
    # this is useless because those data are founded again in the last scf step
    if len(bfgs_data['end']) == 1:
        tmp = re.split(bfgs_set['r_end'], tmp, flags=re.MULTILINE)
        # enable this line to get data from 'end of bfgs' to 'a final scf'
        # last_coordinate = tmp[1]
        # data for next step
        tmp = tmp[0]
    # division of all the oter steps
    bfgs_text = re.split(bfgs_set['r_bfgs_split'], tmp,
                         flags=re.MULTILINE)
    # remove first line if not too long( usually it is just a set of blank
    # spaces)
    if len(bfgs_text[0]) < 30:
        bfgs_text.pop(0)
    bfgs_text = ['number of scf cycles' + x for x in bfgs_text]

    # put all the split data in the right vector
    for x in bfgs_text:
        split_data.append(('bfgs', x))

    if len(bfgs_data['end']) == 1:
        verbose_dict['bfgs_error'] = False
        verbose_dict['bfgs_converged'] = True if \
            len(bfgs_data['bfgs_converged']) >= 1 else False
        if verbose_dict['bfgs_converged']:
            bfgs_data['criteria'] = bfgs_data['criteria'][0]
            verbose_dict[bfgs_data['criteria'][0]] = bfgs_data['criteria'][1]
            verbose_dict[bfgs_data['criteria'][2]] = bfgs_data['criteria'][3]
            verbose_dict[bfgs_data['criteria'][4]] = bfgs_data['criteria'][5]
    else:
        verbose_dict['bfgs_error'] = True

    if len(bfgs_data['final_scf']) == 1:
        split_data.append(('scf', scf_last_text))

    if verbose:
        return if_bfgs, split_data, verbose_dict
    else:
        return if_bfgs, split_data


def scf_in(text, scf_out_feeder=False):
    """
    given data of SCF calculation output return all the data of that simulation
    raise several error if something went wrong,
    """
    simulation = {}
    for x in scf_input:
        data = re.findall(scf_input[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        else:
            simulation[x[2:]] = data

    # normalization of cell description
    cell_side = simulation.pop('cell_side')
    simulation['cell_side'] = [x[1:] for x in cell_side]

    # normalization of atom description
    simulation['atom_description'] = {}
    for x, y in zip(simulation.pop('dspecies'),
                    simulation.pop('pseudopotential')):
        if x[0] == y[1]:
            pseudo_name = y[2].split('/')[-1]
            simulation['atom_description'][y[1]] = (y[0], x[1], x[2],
                                                    pseudo_name)
        else:
            raise ValueError('Inconsistency in QE output')
    if len(simulation['atom_description']) < simulation['nspecies']:
        raise CorruptedData('some atom are not well described', simulation,
                            'atom_description')

    # creating the conversion table
    conversion = {int(v[0]): k for k, v in
                  simulation['atom_description'].items()}
    # number of atom:
    nat = int(simulation['natoms'])

    # normalization of atomic positions, this part should be done better
    # idea: force a division on work cristallographic axes
    crystal_text = re.split(scf_input_cryst['r_cryst_split_begin'],
                            text, flags=re.MULTILINE)[1]
    crystal_text = re.split(scf_input_cryst['r_cryst_split_end'],
                            crystal_text, flags=re.MULTILINE)[0]
    a_pos = re.findall(scf_input_cryst['r_apos'],
                       crystal_text,
                       re.MULTILINE)
    if len(a_pos) < nat:
        raise CorruptedData('some position are missing', simulation,
                            'atom_position')

    if scf_out_feeder:
        return (text, nat, conversion, a_pos, simulation)
    else:
        return simulation


def scf_out(text, nat, atom_conversion, positions, simulation={}):
    """
    given data of SCF calculation output return all the data of that simulation
    raise several error if something went wrong,
    nat: number of atom
    atom conversion is needed because scf does not provide atomic name.
    """
    keys_not_found = []
    for x in scf_output:
        data = re.findall(scf_output[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        elif len(data) == 0:
            keys_not_found.append[x[2:]]
        else:
            simulation[x[2:]] = data

    # the normalizations MUST BE DONE in the same order as the data are
    # collected becouse the first that fails will rise an error and all the
    # others wont be applied.

    # normalization of force and positions
    simulation['atom'] = []
    force = simulation.pop('force')[:nat]

    # zip by doc cut the lenght of the result to the shorter.
    for x, y in zip(positions, force):
        if x[0] == y[0] and x[1] == atom_conversion[int(y[1])]:
            simulation['atom'].append((x[0], x[1], x[2:], y[2:]))
        else:
            raise CorruptedData('Error in conversion step, check qe output',
                                simulation)

    if len(force) < nat:
        # this means that not enouth forces have been found on the output file
        raise CorruptedData('not enought forces, damage data', simulation,
                            'Forces')

    # normalization of stress and pressure information
    simulation['stress_tesnsor'] = []
    simulation['pressure_tesnsor'] = []
    if 'stress_units' in keys_not_found:
        raise CorruptedData('stress units not found', simulation,
                            'stress_Units')
    if 'pressure' in keys_not_found:
        raise CorruptedData('pressure not found', simulation,
                            'Pressure_Units')
    else:
        simulation['pressure'] = [simulation['pressure'][1],
                                  simulation['pressure'][0]]

    for x in simulation.pop('stress_and_kbar_tensor'):
        simulation['stress_tensor'].append(x[:3])
        simulation['pressure_tensor'].append(x[3:])
    if len(simulation['stress_tensor']) < 3:
        raise CorruptedData('stress tensor and pressure tensor incomplete',
                            simulation, 'stress_tensor', 'stress_tensor')
    return simulation


def scf_complete(text):
    """
    given the output of a complete scf step it returns a dictionary
    with all the data. The output MUST HAVE AT LEAST the '! energy'
    line.
    """
    simulation = {}
    for x in scf_input:
        data = re.findall(scf_input[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        else:
            simulation[x[2:]] = data
    for x in scf_output:
        data = re.findall(scf_output[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        else:
            simulation[x[2:]] = data

    # the normalizations MUST BE DONE in the same order as the data are
    # collected becouse the first that fails will rise an error and all the
    # others wont be applied.

    # normalization of atom description
    simulation['atom_description'] = {}
    for x, y in zip(simulation.pop('dspecies'),
                    simulation.pop('pseudopotential')):
        if x[0] == y[1]:
            pseudo_name = y[2].split('/')[-1]
            simulation['atom_description'][y[1]] = (y[0], x[1], x[2],
                                                    pseudo_name)
        else:
            raise ValueError('Inconsistency in QE output')

    conversion = {int(v[0]): k for k, v in
                  simulation['atom_description'].items()}

    # normalization of cell description
    cell_side = simulation.pop('cell_side')
    simulation['cell_side'] = [x[1:] for x in cell_side]

    # normalization of force and positions
    simulation['atom'] = []
    nat = int(simulation['natoms'])
    pos = simulation.pop('apos')[nat:]
    force = simulation.pop('force')[:nat]

    if len(force) < nat:
        # try to save as much data as possible
        for x in pos:
            simulation['atom'].append((x[0], x[1], x[2:]))
        raise CorruptedData('not enought forces, damage data', simulation)
    for x, y in zip(pos, force):
        if x[0] == y[0] and x[1] == conversion[int(y[1])]:
            simulation['atom'].append((x[0], x[1], x[2:], y[2:]))
        else:
            raise ValueError('Error in conversion step')

    # normalization of stress and pressure information
    simulation['stress_tesnsor'] = []
    simulation['pressure_tesnsor'] = []
    for x in simulation.pop('stress_and_kbar_tensor'):
        simulation['stress_tesnsor'].append(x[:3])
        simulation['pressure_tesnsor'].append(x[3:])
    return simulation


def bfgs_complete(text):
    """
    given the output of a complete bfgs step it returns a dictionary
    with all the data. The output MUST HAVE AT LEAST the '! energy'
    line.
    """

    simulation = {}
    for x in scf_data_out:
        data = re.findall(scf_data_out[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        else:
            simulation[x[2:]] = data
    for x in bfgs_data_out:
        data = re.findall(bfgs_data_out[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        else:
            simulation[x[2:]] = data

    # normalization of cell side units
    try:
        cell_side_units = simulation['cell_side_units'][0].split('=')
    except IndexError:
        raise CorruptedData('no cell_side_units', simulation)
    if len(cell_side_units) == 2:
        if cell_side_units[0] == 'alat':
            simulation['cell_side_units'] = cell_side_units[0]
            simulation['alat'] = cell_side_units[1]

    # normalization of force and positions
    simulation['atom'] = []
    pos = simulation.pop('apos')
    conversion = []
    for x in pos:
        if x[0] not in conversion:
            conversion.append(x[0])
    conversion = {i + 1: j for i, j in enumerate(conversion)}
    nat = len(pos)
    force = simulation.pop('force')[:nat]
    if len(force) < nat:
        if len(force) < nat:
            for x in pos:
                simulation['atom'].append((x[0], x[1:]))
        raise CorruptedData('not enought forces, damage data', simulation)
    for x, y in zip(pos, force):
        if x[0] == conversion[int(y[1])]:
            simulation['atom'].append((y[0], x[0], x[1:], y[2:]))
        else:
            if DEBUG:
                print('D - bfgs_complete')
                print(text)
                print(conversion)
                print(x[0])
                print(y[1])
            raise ValueError('Error in conversion step')
    return simulation
