"""
Add the other masks.

"""
import numpy as np
import pickle
import xarray as xr

import gfun

Gr =gfun.gstart()
# select and increment grid file
in_fn = gfun.select_file(Gr)
out_fn = gfun.increment_filename(in_fn, '_x')

# get the grid from NetCDF
ds = xr.open_dataset(in_fn)
h = ds.h.values
mask_rho = ds.mask_rho.values

# load the default choices
dch = pickle.load(open(Gr['gdir'] / 'choices.p', 'rb'))

# enforce min depth
if dch['use_min_depth']:
    # set min depth everywhere
    h[ h <= dch['min_depth'] ] = dch['min_depth']

# Make the masks.

mask_u_bool = (mask_rho[:, 1:] == 0) | (mask_rho[:, :-1] == 0)
mask_u = np.ones_like(mask_u_bool, dtype=int)
mask_u[mask_u_bool] = 0

mask_v_bool = (mask_rho[1:, :] == 0) | (mask_rho[:-1, :] == 0)
mask_v = np.ones_like(mask_v_bool, dtype=int)
mask_v[mask_v_bool] = 0

mask_psi_bool = ( (mask_rho[1:, 1:] == 0) | (mask_rho[:-1, :-1] == 0) |
                (mask_rho[1:, :-1] == 0) | (mask_rho[:-1, 1:] == 0) )
mask_psi = np.ones_like(mask_psi_bool, dtype=int)
mask_psi[mask_psi_bool] = 0

# save the updated mask and h
ds.update({'h': (('eta_rho', 'xi_rho'), h)})
ds['mask_u'] = (('eta_u', 'xi_u'), mask_u)
ds['mask_v'] = (('eta_v', 'xi_v'), mask_v)
ds['mask_psi'] = (('eta_psi', 'xi_psi'), mask_psi)
ds['spherical'] = 'T'
ds.to_netcdf(out_fn)
ds.close()



