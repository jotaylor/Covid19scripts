'''
Script to merge together the US county shapefiles and population 
data into a single pandas dataframe. This can then be used with
the COVID19 data to make some maps.
'''
import pandas as pd
import geopandas as gpd
import numpy as np
from astropy.time import Time
import matplotlib.pyplot as plt
import sys

def get_data():

    #Reading in government tables.
    allpop = pd.read_csv('data/county_pop.csv') 
    map_df = gpd.read_file('data/cb_2019_us_county_500k.shp')


    #Extracting population information
    allpop['FIPS'] = [f'{st:0>2d}{cty:0>3d}' for st,cty in np.array(allpop[['STATE','COUNTY']].values,dtype=int)]

    pop = allpop[['FIPS','POPESTIMATE2019']] 


    #Extracting map information
    map_df['FIPS'] = [f'{st:0>2d}{cty:0>3d}' for st,cty in np.array(map_df[['STATEFP','COUNTYFP']].values,dtype=int)]  

    maps = map_df[['FIPS','geometry']]

    data = maps.merge(pop,on='FIPS')
    data.FIPS = data.FIPS.astype('float')


    #Reading in the COVID data
    covid = pd.read_csv('data/time_series_covid19_confirmed_US.csv',
                        index_col='FIPS')
    countynames = covid.Combined_Key
    covid.drop(columns=['UID','iso2','iso3','code3','Combined_Key',
                        'Admin2','Province_State','Country_Region',
                        'Lat','Long_'],
               inplace=True)

    covid = covid.diff(axis=1)


    dt_idx = pd.to_datetime(covid.columns)
    covid = covid.T
    covid = covid.reindex(dt_idx)
    covid = covid.iloc[5:].resample('W',label='right',closed='right').sum()
    #covid = covid.diff()
    covid.rename(index=str,inplace=True)
    covid = covid.T
    covid = pd.concat([countynames,covid],axis=1,ignore_index=False)

    data = data.merge(covid,on='FIPS') 

    data[data.columns[4:]] = 1000*data[data.columns[4:]].div(data.POPESTIMATE2019,axis=0)

    return data

def do_maps(data):

    cmap = 'seismic'
    vmin,vmax = -250,250
    data.to_crs('EPSG:2163',inplace=True)

    for col in data.columns[4:]:

        fig,ax = plt.subplots(1,figsize=(24,15.44),num=col)
        ax.axis('off')
       
        sm = plt.cm.ScalarMappable(cmap=cmap,
                                   norm=plt.Normalize(vmin=vmin,vmax=vmax)
                                   )
        sm.set_array([])
        
        #cbar = fig.colorbar(sm)
        #cbar.set_ticks([])
       
        data.plot(column=col,cmap='Reds', scheme='percentiles',
                  classification_kwds={'pct':[90,95,100]},
                  linewidth=0.25,ax=ax,edgecolor='0.5')
        ax.set_xlim(-2.2e6,2.7e6)
        ax.set_ylim(-2.3e6,9e5)
        ax.annotate(f'{col[:10]}',xy=(0.5,0.95),xycoords='figure fraction',
                   horizontalalignment='center',fontsize=32)

        #plt.suptitle(col[:10],fontsize='x-large')
        plt.savefig(f'plots/maps/{col[:10]}.jpg',bbox_inches='tight')

        plt.close(col)

if __name__ == "__main__":

    import matplotlib
    matplotlib.use('Agg')


    domaps = bool(int(sys.argv[1]))

    data = get_data()

    if domaps:

        do_maps(data)

