import re

DEBUG = False


class CorruptedData(Exception):
    def __init__(self, message, data):
        super(CorruptedData, self).__init__(message)
        # clean the data form empty keys
        data_celaned = {k: v for k, v in data.items() if v != []}
        self.parsed_data = data_celaned


# util to regexp
unit = r'(\(?(?:Ry|a\.u\.|bohr|\/|ang)+\)?(?:\^|\*\*)?\d*\)?)'
atoms_name = r'(?:C|H|O|N)'

# information of scf
scf_set = dict(
    r_PWSCF_version=r'^ *Program PWSCF (.+) starts',
    r_pseudopotential=r'^ *file *([\w_\-\.]+\.UPF)',
    r_bli=r'^ *bravais-lattice index *= *(\d+)',
    r_alat=r'^ *lattice parameter \(alat\) *= *([\d\.\+\-]+) *{}'.format(unit),
    r_unit_cell_volume=r'^ *unit-cell volume *= *([\d\.\+\-]+) *{}'.format(
                       unit),
    r_cell_side_units=r' *crystal axes: \(cart. coord. in units of (alat)\)',
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
    r_mixing=r'^ *mixing beta *= *([\d\.\+\-]+)',
    r_apos=r'^ +(\d+) +({})[^=]+= \( +([\d\+\-\.]+) +([\d\+\-\.]+) +'
           '([\d\+\-\.]+) +\)'.format(atoms_name))

# data of scf
# TODO, the pressure calculation is carried out in different way
# on different QE version
# here we have the most common version

scf_data_out = dict(
    r_total_energy=r'^![\w =]+([\d\.\+\- ]+){}'.format(unit),
    r_E_hartree=r'^ +hartree \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_onelectron=r'^ +one-electron \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_xc=r'^ +xc \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_ewald=r'^ +ewald \w+ += +([\d\.\+\-]+) +{}'.format(unit),
    r_E_paw=r'^ +one-center paw \w+\. += +([\d\.\+\-]+) +{}'.format(unit),
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
    r_bfgs_converged=r' +bfgs converged in +(\d+) +scf cycles and +(\d+) +'
                     'bfgs steps',
    r_bfgs_not_converged=r'^ +The maximum number of steps has been reached.',
    r_criteria=r'^ +\(criteria: +(energy) < ([\d\.\+\-E]+),'
               ' +(force) < ([\d\.\+\-E]+),'
               ' +(cell) < ([\d\.\+\-E]+)\)',
    r_end=r'^ +End of BFGS Geometry Optimization',
    r_start=r'^ +BFGS Geometry Optimization',
    r_nstep=r'^ *nstep *= *(\d+)',
    r_recalculation=r'The G-vectors are recalculated for the final unit cell')

# data of bfgs:
bfgs_data_out = dict(
    r_unit_cell_volume=r'^ *new unit-cell volume *= *([\d\.\+\-]+) *{}'.format(
                       unit),
    r_cell_side_units=r'CELL_PARAMETERS \(([\w ]+= +[\d\.\+\-]+|bohr)\)',
    r_cell_side=r'^ {2,3}([\d\+\-\.]+) +([\d\+\-\.]+) +([\d\+\-\.]+)$',
    r_apos_units=r'ATOMIC_POSITIONS \((.+)\)',
    r_apos=r'^({}) +([\d\+\-\.]+) +([\d\+\-\.]+) +([\d\+\-\.]+)$'
                .format(atoms_name))

# closing string:
r_close = r'JOB DONE'


def scf_complete(text):
    """
    given the output of a complete scf step it returns a dictionary
    with all the data. The output MUST HAVE AT LEAST the '! energy'
    line.
    """
    simulation = {}
    for x in scf_set:
        data = re.findall(scf_set[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        else:
            simulation[x[2:]] = data
    for x in scf_data_out:
        data = re.findall(scf_data_out[x], text, re.MULTILINE)
        if len(data) == 1:
            simulation[x[2:]] = data.pop()
        else:
            simulation[x[2:]] = data

    # the normalizations MUST BE DONE in the same order as the data are
    # collected becouse the first that fails will rise an error and all the
    # others wont be applied.

    # normalization of atom description
    simulation['atom_description'] = []
    for x, y in zip(simulation.pop('dspecies'),
                    simulation.pop('pseudopotential')):
        simulation['atom_description'].append((x[0], x[1], x[2], y))

    conversion = {i + 1: x[0] for i, x in
                  enumerate(simulation['atom_description'])}

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
    cell_side_units = simulation['cell_side_units'].split('=')
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
