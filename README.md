# quantum espresso output parser
Up to now this is a parser wanna be, so use it at your own risk.

It is developed arround SCF + BFGS calculations so if other calculations are supported it is just by chance. The code has been tested over more than 500 output.

If options capable of forcing the calculation to continue even if there has been no convergence are active in the input file the code wont fail but the data of the steps that didn't converged could be unreliable. 

# How to use it:
what you need is file_parser(file_name) function, in data_magic module (documentation in line).
Furthermore you need to add the atoms name that you are going to use in the string atoms_name in 'parser.py'

like:

```python
atoms_name = r'(?:C|H|O|N)'
atoms_name = r'(?:C|H|O|N|Ar)'
```


Apply me just apply it to all the files in a folder and give you the total result as a json with all the simulations.



# data structure:
```
id_simulation:
        |
        + file name
        + id  previous simulation
        + id next simulation
        + id first simulation of the family
        + id last simulation of the family
        + number in the sequence (i, n_tot)
        + bli (bravais lattice index)
        + alat
        + unit_cell_volume
        + cell_side
        + natoms
        + nspecies
        + nelectrons
        + nksstates
        + cutoff
        + charge_cutoff
        + threshold
        + mixing
        + cell_side_units (TODO, it is alat)
        + atoms
        |     |
        |     + number of the atom
        |     + type
        |     + position (crystal coordinate)
        |     |        |
        |     |        + v1
        |     |        + v2
        |     |        + v3
        |     + force (Ry/au)
        |           |
        |           + v1
        |           + v2
        |           + v3
        + cell (crystal coordinate, alat)
        |    |
        |    + v1
        |    + v2
        |    + v3
        + alat of cell
        + total_energy
        + E_hartree
        + E_onelectron
        + E_xc
        + E_ewald
        + E_paw
        + stress_units
        + atom_description (pseudopotential, mass, etc)
        + stress_tesnsor 
        + pressure_tesnsor
        
        if last:
        |
        + bfgs_converged = bool
        + recalculation = bool
 
        if damage :
        |
        + damage = True => energy ok, other data could be corrupted
        |
        + damage_next = True => 
            there is one more corrupted simulation in the file that has been discarded 
```
# Read the log:
YOU MUST DO IT!

For every corrupted file there is the discarded part of data with on top a bunch of useless information. Check if the discarded part of data is ok with what you expected. 

If I will have time I will work on improving the data recovery.


