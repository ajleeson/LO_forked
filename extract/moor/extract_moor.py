"""
This is code for doing mooring extractions.

Test on mac in ipython:

run extract_moor.py -g cas6 -t v3 -x lo8b -ro 2 -0 2019.07.04 -1 2019.07.06 -get_all True

Use -test True to keep the folder full of temporary files.

The performance on this is excellent, taking about 24 minutes for a year of hourly records
on perigee with cas6_v3_lo8b and all flags True.

"""

from pathlib import Path
import sys
from datetime import datetime, timedelta

pth = Path(__file__).absolute().parent.parent.parent / 'alpha'
if str(pth) not in sys.path:
    sys.path.append(str(pth))
import extract_argfun as exfun

Ldir = exfun.intro() # this handles the argument passing
result_dict = dict()
result_dict['start_dt'] = datetime.now()

# ****************** CASE-SPECIFIC CODE *****************

import Lfun
import zrfun, zfun
from time import time
from subprocess import Popen as Po
from subprocess import PIPE as Pi
import numpy as np
import xarray as xr

tt00 = time()

# set output location
out_dir = Ldir['LOo'] / 'extract' / Ldir['gtagex'] / 'moor'
temp_dir = Ldir['LOo'] / 'extract' / Ldir['gtagex'] / 'moor' / ('temp_' + Ldir['sn'])
Lfun.make_dir(out_dir)
Lfun.make_dir(temp_dir, clean=True)
moor_fn = out_dir / (Ldir['sn'] + '_' + Ldir['ds0'] + '_' + Ldir['ds1'] + '.nc')
moor_fn.unlink(missing_ok=True)
print(moor_fn)

# get indices for extraction
in_dir0 = Ldir['roms_out'] / Ldir['gtagex']
lon = Ldir['lon']
lat = Ldir['lat']
G, S, T = zrfun.get_basic_info(in_dir0 / ('f' + Ldir['ds0']) / 'ocean_his_0001.nc')
Lon = G['lon_rho'][0,:]
Lat = G['lat_rho'][:,0]    
# error checking
if (lon < Lon[0]) or (lon > Lon[-1]):
    print('ERROR: lon out of bounds ' + out_fn.name)
    sys.exit()
if (lat < Lat[0]) or (lat > Lat[-1]):
    print('ERROR: lat out of bounds ' + out_fn.name)
    sys.exit()
# get indices
ilon = zfun.find_nearest_ind(Lon, lon)
ilat = zfun.find_nearest_ind(Lat, lat)
# more error checking
if G['mask_rho'][ilat,ilon] == False:
    print('ERROR: rho point on land mask ' + out_fn.name)
    sys.exit()
if Ldir['get_vel'] or Ldir['get_surfbot']:
    if G['mask_u'][ilat,ilon] == False:
        print('ERROR: u point on land mask ' + out_fn.name)
        sys.exit()
    if G['mask_v'][ilat,ilon] == False:
        print('ERROR: v point on land mask ' + out_fn.name)
        sys.exit()
        
fn_list = Lfun.get_fn_list(Ldir['list_type'], Ldir, Ldir['ds0'], Ldir['ds1'])

vn_list = 'h,zeta'
if Ldir['get_tsa']:
    vn_list += ',salt,temp,AKs,AKv'
if Ldir['get_vel']:
    vn_list += ',u,v,w'
if Ldir['get_bio']:
    vn_list += ',NO3,phytoplankton,zooplankton,detritus,Ldetritus,oxygen,alkalinity,TIC'
if Ldir['get_surfbot']:
    vn_list += ',Pair,Uwind,Vwind,shflux,ssflux,latent,sensible,lwrad,swrad,sustr,svstr,bustr,bvstr'
    
proc_list = []
N = len(fn_list)
print('\nTimes to extract =  %d' % (N))
for ii in range(N):
    fn = fn_list[ii]
    # extract one day at a time using ncks
    count_str = ('000000' + str(ii))[-6:]
    out_fn = temp_dir / ('moor_temp_' + count_str + '.nc')
    cmd_list1 = ['ncks',
        '-v', vn_list,
        '-d', 'xi_rho,'+str(ilon), '-d', 'eta_rho,'+str(ilat)]
    if Ldir['get_vel'] or Ldir['get_surfbot']:
        cmd_list1 += ['-d', 'xi_u,'+str(ilon), '-d', 'eta_u,'+str(ilat),
            '-d', 'xi_v,'+str(ilon), '-d', 'eta_v,'+str(ilat)]
    cmd_list1 += ['-O', str(fn), str(out_fn)]
    proc = Po(cmd_list1, stdout=Pi, stderr=Pi)
    proc_list.append(proc)
    
    if (np.mod(ii,100) == 0): # 100
        print(str(ii), end=', ')
        sys.stdout.flush()
        if (np.mod(ii,1000) == 0) and (ii > 0): # 1000
            print(str(ii))
            sys.stdout.flush()
    elif (ii == N-1):
        print(str(ii))
        sys.stdout.flush()
    
    
    # Nproc controls how many ncks subprocesses we allow to stack up
    # before we require them all to finish.  It appears to work even
    # with Nproc = 100, although this may slow other jobs.
    Nproc = 100
    if (np.mod(ii,Nproc) == 0) or (ii == N-1):
        for proc in proc_list:
            proc.communicate()
        # make sure everyone is finished before continuing
        proc_list = []

# concatenate the day records into one file
# This bit of code is a nice example of how to replicate a bash pipe
pp1 = Po(['ls', str(temp_dir)], stdout=Pi)
pp2 = Po(['grep','moor_temp'], stdin=pp1.stdout, stdout=Pi)
cmd_list = ['ncrcat','-p', str(temp_dir), '-O',str(moor_fn)]
proc = Po(cmd_list, stdin=pp2.stdout, stdout=Pi)
proc.communicate()

# add z_coordinates to the file using xarray
xs = xr.load_dataset(moor_fn)
xs = xs.squeeze() # remove singleton dimensions
zeta = xs.zeta.values
NT = len(zeta)
hh = xs.h.values * np.ones(NT)
z_rho, z_w = zrfun.get_z(hh, zeta, S)
# the returned z arrays have vertical position first, so we 
# transporse to put time first for the mooring, to be consistent with
# all other variables
xs['z_rho'] = (('ocean_time', 's_rho'), np.transpose(z_rho.data))
xs['z_w'] = (('ocean_time', 's_w'), np.transpose(z_w.data))
xs.z_rho.attrs['units'] = 'm'
xs.z_w.attrs['units'] = 'm'
xs.z_rho.attrs['long name'] = 'vertical position on s_rho grid, positive up'
xs.z_w.attrs['long name'] = 'vertical position on s_w grid, positive up'
# add units to salt
xs.salt.attrs['units'] = 'g kg-1'
# update the time long name
xs.ocean_time.attrs['long_name'] = 'Time [UTC]'
# update format attribute
xs.attrs['format'] = 'netCDF-4'
# and save to NetCDF (default is netCDF-4, and to overwrite any existing file)
xs.to_netcdf(moor_fn)
    
# clean up
if not Ldir['testing']:
    Lfun.make_dir(temp_dir, clean=True)
    temp_dir.rmdir()

print('\nTotal Elapsed time was %0.2f sec' % (time()-tt00))

# test for success 
if moor_fn.is_file():
    result_dict['result'] = 'success' # success or fail
else:
    result_dict['result'] = 'fail'

# *******************************************************

result_dict['end_dt'] = datetime.now()
