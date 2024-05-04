from dash import Dash, dcc, html, Input, Output, callback
import os
import numpy as np
import pandas as pd
import matplotlib  
import matplotlib.pyplot as plt
from ChannelAttribution import *
import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go


colors = {
    'background': '#eee6f3',
    'header': '#57068c', 
    'text': '#000000'
}

# load the data
Data = pd.read_csv('MTA_Input.csv')
channel = pd.read_csv("NintendoMapping.csv")

# some counting
Data['channels_count'] = Data.str_path.apply(lambda x: x.count("&"))
Data['users_count'] = Data.user_id.apply(lambda x: x.count(" ")+1)

total_journey = Data.converters.sum()+Data.nonconverters.sum()

df = Data.groupby(['first_touch','last_touch']).agg(
        conv = pd.NamedAgg(column= 'converters', aggfunc='sum'), 
        nonconv = pd.NamedAgg(column= 'nonconverters', aggfunc='sum'),
        )
df['cnt'] = df.conv + df.nonconv
df = df.reset_index()
df = df[df['first_touch'].isin(['Awareness Search Ads'])]

### ----- ----- ----- -----
## Dash 
### elements
### ----- ----- ----- -----

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

header = html.Div([
    html.Div(children='Budget Allocation Analysis for Nintendo on Amazon platform', 
             style={'color': colors['text'], 
                    'width': '70%' }
    ),
    html.H1(
        children='AdFlow+',
        style={
            'textAlign': 'right',
            'color': colors['header'],
            'width': '30%'
        }
    ),
    
],style={'display': 'flex', 'flexDirection': 'row'})




def summary_box(cnt, unit):
    box = html.Div([
        html.H2(cnt), 
        html.P(unit)
    ], style={'text-align': 'center'})
    return box


def summary_box_w_graph(cnt, unit, graph_id):
    box = html.Div([
        summary_box(cnt, unit), 
        dcc.Graph(id = graph_id, style={'width':'250px','height':'250px'}),
        html.Br(),
    ], style={'border':"2px black solid",
              'border-radius': '15px'}
    )
    return html.Div(box,style={'border':"7px #eee6f3 solid"})

### ----- ----- ----- -----
### ----- layout tabs -----
### ----- ----- ----- -----

## tab for overall summary
pie_graphs = html.Div([
    summary_box_w_graph(
        Data.converters.sum(),
        "conversion",
        'fig_conv_count'
    ),
    summary_box_w_graph(
        Data.promotion.sum(), 
        "Promotion",
        'fig_prom_count'
    ),
    summary_box_w_graph(
        Data.web.sum(), 
        "Web users",
        'fig_brow_count'
    ),
], style={'display': 'flex', 'flexDirection': 'row'},  
)

Tab_summary = html.Div(
    id = 'tab-summary',
    children = [
        html.Div(
            id = 'total_overview', 
            children=[
                summary_box(total_journey, 'shopping journeies'),
                pie_graphs,
            ],
        ),
        html.Div(
            id = 'path_overview', 
            children = [
                dcc.Graph(id = 'fig_histogram', style={'width':'500px'}),
            ]
        ), 
    ], 
    style={'display': 'flex',  'flexDirection': 'row'}, 
)


## Tab for analysis by first/last touch
## see call back function below

F_L_filter = html.Div([
    dcc.RadioItems(
        options = ['First Touch', 'Last Touch'], 
        value = 'First Touch', 
        id = 'Radio-First_Last'
    ),
    dcc.Store(id='intermediate-value')
])

F_L_bar_chart = html.Div([
    dcc.Graph( id = 'fig-first_last_count' )
])


Tab_touch = html.Div(
    children= [F_L_filter, F_L_bar_chart], 
    style={'display': 'flex', 'flexDirection': 'row'}, 
)

## Tab for the Sankey diagram
Conv_filter = html.Div([
    html.Div('Show only'), 
    dcc.RadioItems(
        options=['Converters', 'Non Converters', 'Total'], 
        value = 'Converters', 
        id = 'filter-convert',
    )
])

First_filter = html.Div([
    html.Div('First Touch'),
    dcc.Checklist(
        options=Data.first_touch.unique(), 
        value=Data.first_touch.unique(), 
        id = 'filter-First', 
    ), 
])

Last_filter = html.Div([
    html.Div('Last Touch'),
    dcc.Checklist(
        options=Data.last_touch.unique(), 
        value=Data.last_touch.unique(), 
        id = 'filter-Last', 
    ), 
])

Tab_Sankey = html.Div([
    html.Div([Conv_filter, First_filter, Last_filter]),
    dcc.Graph( id = 'fig-Sankey', style={'height':'600px'})
], style={'display': 'flex', 'flexDirection': 'row'}
)


### ----- ----- ----- -----
### ----- Final Layout -----
### ----- ----- ----- -----

app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
    header,
    dcc.Tabs([
        dcc.Tab(label="Summary", children= Tab_summary), 
        dcc.Tab(label="Touch Points Analysis", children= Tab_touch),
        dcc.Tab(label="Flow Sankey", children= Tab_Sankey),
    ])
])



### ----- ----- ----- -----
### ----- All call backs functions below -----
### ----- ----- ----- -----


## Pivot First/Last Touch count, group by Channel
@callback(
    Output('intermediate-value', 'data'),
    Input('Radio-First_Last', 'value')
)
def Count_by_Touch(value):
    touch = 'first_touch' if value == 'First Touch' else 'last_touch'
    stat_data = Data.groupby(touch).agg(
        path_count = pd.NamedAgg(column='path_id', aggfunc='count'),
        conversion = pd.NamedAgg(column='converters', aggfunc='sum'),
        non_conversion = pd.NamedAgg(column='nonconverters', aggfunc="sum"))
    stat_data['conversion_pct'] = round(stat_data.conversion/(stat_data.conversion + stat_data.non_conversion) *100, 3)
    stat_data['non_conversion_pct'] = round(stat_data.non_conversion/(stat_data.conversion + stat_data.non_conversion)*100, 3)
    stat_data = stat_data.reset_index().rename(columns={touch: 'channel'})
    return stat_data.to_json()

@callback(
    Output('fig-first_last_count', 'figure'),
    Input('intermediate-value', 'data'),
    Input('Radio-First_Last', 'value')
)
def update_count_fig(data, touch):
    dff = pd.read_json(data)
    #fig = px.bar(dff, x='channel', y='path_count')
    #fig = px.bar(dff, x='channel', y=['non_conversion','conversion'], title='Count of conversion')
    fig = px.bar(dff, 
                 x=['non_conversion','conversion'], 
                 y='channel', 
                 title='Count of conversion by '+touch, 
                 text_auto= ".2s",
                 orientation='h')
    
    fig.update_yaxes(title=None)
    fig.update_xaxes(title=None, showticklabels=False)
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor=colors['background'] ,
        legend = dict(orientation="h",
                      yanchor="bottom", y=1.0,
                      xanchor="right", x=1.0, 
                      title = None)
    )
    return fig


@callback(
    Output('fig_conv_count', 'figure'),
    Output('fig_prom_count', 'figure'),
    Output('fig_brow_count', 'figure'),
    Input('Radio-First_Last', 'value')
)
def update_pie_fig(value):
    def create_pie(val, name):
        fig = px.pie(values= val, 
                     names= name, 
                     hole=.5, 
                     #textinfo='label+percent',
                     # #title= "Total count"
                     )
        fig.update_traces(hoverinfo='label+percent', textinfo='label+percent')
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
            paper_bgcolor=colors['background'] ,
        )
        return fig

    fig_conv = create_pie([Data.converters.sum(), Data.nonconverters.sum()], ["Converters","Non Conversters"])
    fig_prom = create_pie([Data.promotion.sum(), (total_journey - Data.promotion.sum())], ["Promotion","Non Promotion"])
    fig_brow = create_pie([Data.web.sum(), Data.phone.sum()], ["Web users", "Phone users"])
    return fig_conv, fig_prom, fig_brow


## Histogram channels in path 
@callback(
    Output('fig_histogram', 'figure'),
    Input('Radio-First_Last', 'value')
)
def update_histogram_fig(value):
    fig = px.histogram(Data, x='channels_count', title='Count of Channel in a path')
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor=colors['background']
    )
    return fig


## Sankey
@callback(
    Output('fig-Sankey', 'figure'),
    Input('filter-First', 'value'), 
    Input('filter-Last', 'value'),
    Input('filter-convert', 'value')
)
def update_sankey(First, Last, conv):
    df = Data.groupby(['first_touch','last_touch']).agg(
        conv = pd.NamedAgg(column= 'converters', aggfunc='sum'), 
        nonconv = pd.NamedAgg(column= 'nonconverters', aggfunc='sum'),
        )
    df['cnt'] = df.conv + df.nonconv
    df = df.reset_index()
    
    node = df.first_touch.unique()
    df = df[df['first_touch'].isin(First)]
    df = df[df['last_touch'].isin(Last)]

    for i in range(len(node)):
        df.loc[df.first_touch == node[i], 'first_touch'] = i
        df.loc[df.last_touch == node[i], 'last_touch'] = i

    fig = go.Figure(data=[go.Sankey(
        node = dict(
        pad = 15,
        thickness = 20,
        line = dict(color = "black", width = 0.5),
        label = [*node,*node],
        color = "blue"
        ),
        link = dict(
        source = df.first_touch, 
        target = [x + len(node) for x in df.last_touch],
        value = df.conv if conv == 'Converters' else df.nonconv if conv == 'Non Converters' else df.cnt
    ))])

    fig.update_layout(title_text= conv + " From First Touch to Last Touch")
    
    return fig

app.run_server()