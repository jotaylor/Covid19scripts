'''
Script to make a movie showing the weekly progression of COVID on 
a county level. 
The weekly cases by population, are broken down into nationwide 
percentiles, and shown on a map.  

This script takes the US county shapefiles and population data and 
merges them into a single geopandas dataframe. This is then combined 
with the COVID19 data to make the maps.

Requirements
------------
Besides the python dependencies, this script requires the FFMPEG
be installed on the system. 
'''
from matplotlib.animation import FuncAnimation
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from copy import copy
from astropy.time import Time

#Colormap to use
CMAP = 'hot_r'


#Reading in government tables.
allpop = pd.read_csv('geo_pop_data/county_pop.csv') 
map_df = gpd.read_file('geo_pop_data/cb_2019_us_county_500k.shp')

#Keep only the 50 states and DC
idx = map_df.STATEFP.astype('float')<57
map_df = map_df[idx]

#Extracting population information
allpop['FIPS'] = [f'{st:0>2d}{cty:0>3d}' for st,cty in np.array(allpop[['STATE','COUNTY']].values,dtype=int)]

pop = allpop[['FIPS','POPESTIMATE2019']] 

#Extracting map information
map_df['FIPS'] = [f'{st:0>2d}{cty:0>3d}' for st,cty in np.array(map_df[['STATEFP','COUNTYFP']].values,dtype=int)]  

maps = copy(map_df[['FIPS','geometry','ALAND']])
maps.ALAND = maps.ALAND/2.59e6   #Convert square meters to square miles.

data = maps.merge(pop,on='FIPS')
data.FIPS = data.FIPS.astype('float')


#Reading in the COVID data
covid = pd.read_csv('covid_data/time_series_covid19_confirmed_US.csv',
                    index_col='FIPS')
countynames = covid.Combined_Key
covid.drop(columns=['UID','iso2','iso3','code3','Combined_Key',
                    'Admin2','Province_State','Country_Region',
                    'Lat','Long_'],
           inplace=True)

covid = covid.diff(axis=1)
covid[covid<0.] = 0.  #Removing negative values


dt_idx = pd.to_datetime(covid.columns)
covid = covid.T
covid = covid.reindex(dt_idx)
covid = covid.iloc[5:].resample('W',label='right',closed='right').sum()
covid.rename(index=str,inplace=True)
covid = covid.T
covid = pd.concat([countynames,covid],axis=1,ignore_index=False)

data = data.merge(covid,on='FIPS') 

data[data.columns[5:]] = 1000*data[data.columns[5:]].div(data.POPESTIMATE2019,axis=0)

#Setting the map projection
data.to_crs('EPSG:2163',inplace=True)


#Setting up figure
fig,ax = plt.subplots(1,figsize=(8,5))
ax.axis('off')
ax.set_xlim(-2.2e6,2.7e6)
ax.set_ylim(-2.3e6,9e5)
date_text = ax.text(0.5,0.95,'',transform=ax.transAxes,
                    horizontalalignment='center',fontsize=16)

#Adding a colorbar
sm = plt.cm.ScalarMappable(cmap=CMAP,
                           norm=plt.Normalize(vmin=0,vmax=100))
cbar = fig.colorbar(sm,orientation='horizontal',label='Percentile',
                    fraction=0.025,pad=0.1,aspect=30)
cbar.set_ticks([0,20,40,60,80,100])

#Function that mekes cloropleth
def update_map(col):

    dt1 = Time.now()
    fig1 = data.plot(column=col,cmap=CMAP,scheme='percentiles',
              classification_kwds={'pct':[0,20,40,60,70,80,100]},
              linewidth=0.25,ax=ax,edgecolor='0.5')
    date_text.set_text(f'{col[:10]}')
    print(f'{col[:10]} {(Time.now()-dt1).sec:5.2f}')

#Animation class
ani = FuncAnimation(fig,update_map,data.columns[5:],interval=0,
                    cache_frame_data=False)

#Saving the movie
ani.save('plots/worst_counties.mp4',writer='ffmpeg',fps=1,dpi=200)
