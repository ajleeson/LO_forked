"""
This is the main program for making a box extraction of the daily forecast and sending
the results to the APL server.

This is for making the CRITFC output file, using code from Charles Seaton.

Testing on mac:
run post_main.py -gtx cas6_v3_lo8b -ro 2 -d 2019.07.04 -r backfill -job critfc1 -test True

Run for real on apogee:
python post_main.py -gtx cas6_v0_u0mb -ro 0 -d [today's date string] -r forecast -job critfc1

"""

from pathlib import Path
import sys
from datetime import datetime, timedelta

from lo_tools import post_argfun

Ldir = post_argfun.intro() # this handles all the argument passing
result_dict = dict()
result_dict['start_dt'] = datetime.now()

# ****************** CASE-SPECIFIC CODE *****************

# This will be used for the file names that go to the public server.
share_name_list = ['critfc_salt', 'critfc_temp']

# imports
from subprocess import Popen as Po
from subprocess import PIPE as Pi
from time import time
import shutil
from lo_tools import Lfun

print(' - Creating extraction file for ' + Ldir['date_string'])

# create time range for box extraction
ds0 = Ldir['date_string']
dt0 = datetime.strptime(ds0, Lfun.ds_fmt)
if Ldir['run_type'] == 'backfill':
    ds1 = ds0
elif Ldir['run_type'] == 'forecast':
    ndays = Ldir['forecast_days']
    dt1 = dt0 + timedelta(days=ndays-1)
    ds1 = dt1.strftime(Lfun.ds_fmt)

# these are the names of the files we will create
out_dir = Ldir['LOo'] / 'post' / Ldir['gtagex'] / ('f' + Ldir['date_string']) / Ldir['job']

# critfc code inputs
rundate = Ldir['date_string'].replace('.','-')
depthfile = Ldir['roms_out'] / Ldir['gtagex'] / ('f' + Ldir['date_string']) / 'ocean_his_0001.nc'
hgrid = Ldir['data'] / 'critfc' / 'hgrid.ll'
vgrid = Ldir['LO'] / 'post' / Ldir['job'] / 'vgrid.in'
basedir = Ldir['roms_out'] / Ldir['gtagex']
outdir = out_dir

this_dir = str(Ldir['LO'] / 'post' / Ldir['job']) + '/'
cmd = ['python', this_dir + 'gen_cmop_nudge.py', str(hgrid), str(vgrid), str(depthfile),
    str(basedir), str(outdir), rundate, '-test', str(Ldir['testing'])]
proc = Po(cmd, stdout=Pi, stderr=Pi)
stdout, stderr = proc.communicate()
if True:
    if len(stdout) > 0:
        print(' sdtout '.center(60,'-'))
        print(stdout.decode())
    if len(stderr) > 0:
        print(' stderr '.center(60,'-'))
        print(stderr.decode())

# copy the files to the server
if 'apogee' in Ldir['lo_env']:
    
    share_user = 'parker@liveocean.apl.uw.edu'
    print('Warning: copying extractions to server for sharing only works for parker from apogee.')
    share_dir = '/data/www/liveocean/output/' + 'f' + Ldir['date_string']

    # (i) make the output directory
    cmd_list = ['ssh', share_user, 'mkdir -p ' + share_dir]
    proc = Po(cmd_list, stdout=Pi, stderr=Pi)
    stdout, stderr = proc.communicate()
    Lfun.messages(stdout, stderr, 'Make output directory on server')
    
    for share_name in share_name_list:
        out_fn = out_dir / (share_name + '.nc')
        
        # (ii) copy the extraction to there
        cmd_list = ['scp',str(out_fn), share_user + ':' + share_dir]
        proc = Po(cmd_list, stdout=Pi, stderr=Pi)
        stdout, stderr = proc.communicate()
        Lfun.messages(stdout, stderr, 'Copying extraction to ' + share_dir)
        
        # (iii) then write a little text file to alert users
        done_fn = out_dir / (share_name + '_done.txt')
        done_fn.unlink(missing_ok=True)
        with open(done_fn, 'w') as ffout:
            ffout.write(datetime.now().strftime('%Y.%m.%d %H:%M:%S'))
        cmd_list = ['scp',str(done_fn), share_user + ':' + share_dir]
        proc = Po(cmd_list, stdout=Pi, stderr=Pi)
        stdout, stderr = proc.communicate()
        Lfun.messages(stdout, stderr, 'Copying done file to server')

# -------------------------------------------------------

# test for success
for share_name in share_name_list:
    out_fn = out_dir / (share_name + '.nc')
    if out_fn.is_file():
        result_dict['result'] = 'success'
    else:
       result_dict['result'] = 'fail'
       break

# *******************************************************

result_dict['end_dt'] = datetime.now()
post_argfun.finale(Ldir, result_dict)
