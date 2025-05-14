# ATR camera foot print

this script computes the foof print of airborne camera in real time.

## IMU emulator
you can use a IMU emulator in `emulator_broker` to generate imu data using a MQTT broker.
```
./run_mqtt_broker.sh
```
input data needs to be passed to the emulator in `mqtt_data2groundmark_simulator.py` at the start of the file:
```
indir = '/home/paugam/Data/ATR42/as240051/'
imufile = 'SCALE-2024_SAFIRE-ATR42_SAFIRE_CORE_NAV_100HZ_20241113_as240051_L1_V1.nc'
flightname = 'as240051'
warnings.filterwarnings("ignore", category=UserWarning, module="pyproj")
with xr.open_dataset(indir+imufile) as imu:
    dfimu = imu.to_dataframe()
```

## Foot print calculation
The foot print calculation is base on the orthority librairy and calculated in 'src/data2groundmark.py'
run 
```
python data2groundmark.py
```

## Pyhton Environment
Both the broker emulator and the foot print calculation can be run with the pyhton env listed in `requirements.txt`
