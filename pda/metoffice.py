from __future__ import print_function, division
import pandas as pd
import numpy as np

"""
Functions for loading data from the UK metoffice.
"""

def open_daily_xls(filename, sheet='HEATHROW'):
    """Opens an XLS file from the UK met office.

    Args:
        filename (str)
        sheet (str): optional.  Defaults to HEATHROW

    Returns:
        pd.DataFrame with a PeriodIndex in UTC.
            Some columns have an additional .description field
            used for plotting descriptions on graphs (includes some
            LaTeX markup).
    """
    xls = pd.ExcelFile(filename)
    df = xls.parse(sheet, skiprows=4, skip_footer=4, na_values=['n/a'], 
                   parse_dates=True, index_col=0, parse_cols=10)

    columns = {
    u'Daily Maximum Temperature (0900-0900) (\xb0C)': 'max_temp',
    u'Daily Minimum Temperature (0900-0900) (\xb0C)': 'min_temp',
    u'Daily Mean Temperature from Hourly Data (0900-0900) (\xb0C)': 'mean_temp',
    u'Daily Mean Windspeed (0100-2400) (knots)': 'mean_windspeed',
    u'Daily Maximum Gust (0100-2400) (knots)': 'max_gust',
    u'Daily Total Rainfall (0900-0900)(mm)': 'rainfall',
    u'Daily Total Global Radiation (KJ/m2)': 'radiation',
    u'Daily Total Sunshine (0100-2400) (hrs)': 'sunshine',
    u'Daily Minimum Grass Temperature (0900-0900) (\xb0C)': 'max_grass_temp',
    u'Daily Minimum Concrete Temperature (0900-0900) (\xb0C)': 'max_concrete_temp'
    }

    descriptions = {
        'radiation': 'daily total global radiation $MJ/m^{2}$',
        'max_temp': 'daily maximum temperature $\degree C$',
        'min_temp': 'daily minimum temperature $\degree C$',
        'mean_temp': 'daily mean temperature from hourly data $\degree C$'
    }
    
    df = df.rename(columns=columns)
    df = df.tz_localize('UTC').to_period('D')
    
    # the rainfall column contains "tr" and "n/a".  
    # "tr" means "trace" (less than 0.05mm).  Replace "tr" with 0.04
    df['rainfall'][df['rainfall'] == 'tr'] = 0.04
    df['rainfall'] = df['rainfall'].astype(np.float)

    df['radiation'] /= 1000

    for key, val in descriptions.iteritems():
        print("adding a 'description' field for", key)
        df[key].description = val

    return df

def get_long_name(short_name):
    long_names = {'radiation': 'solar radiation'}
    short_name = short_name.replace('_', ' ')
    try:
        return long_names[short_name]
    except KeyError:
        return short_name
