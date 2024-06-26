from dash import Dash, dcc, html, Input, Output, callback, callback_context
import os
import numpy as np
import pandas as pd
from ChannelAttribution import *
import plotly.io as pio
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

### ----- ----- ----- -----
## NYU Color Palette
## https://www.nyu.edu/employees/resources-and-services/media-and-communications/nyu-brand-guidelines/designing-in-our-style/nyu-colors.html
### ----- ----- ----- -----
colors = {
    'background': '#ffffff', #white
    'plot_bg': '#ffffff', #white
    'plot_bg_2': '#eee6f3', #Light Violet 2
    'header': '#57068c', 
    'text': '#000000'
}

conv_colors = { 
    'conversion': "#8900e1", #Ultra Violet
    'non-conversion' : "#b8b8b8",  #Medium Gray 2
}

model_colors = {
    'markov_model':'#8900e1', #Ultra Violet
    'linear_touch':'#6d6d6d', #Medium Gray 1
    'last_touch':'#b8b8b8', #Medium Gray 2
    'first_touch':'#d6d6d6', # Medium Gray 3
}

### ----- ----- ----- ----- -----
### -----  load the data -----
### ----- ----- ----- ----- -----
Data = pd.read_csv('MTA_Input.csv')
#channel = pd.read_csv("NintendoMapping.csv")

# some counting
Data['channels_count'] = Data.str_path.apply(lambda x: x.count("&"))
Data['users_count'] = Data.user_id.apply(lambda x: x.count(" ")+1)

unique_channel_cnt = Data.channels_count.sort_values().unique()

df = Data.groupby(['first_touch','last_touch']).agg(
        conv = pd.NamedAgg(column= 'converters', aggfunc='sum'), 
        nonconv = pd.NamedAgg(column= 'nonconverters', aggfunc='sum'),
        )
df['cnt'] = df.conv + df.nonconv
df = df.reset_index()
df = df[df['first_touch'].isin(['Awareness Search Ads'])]

# function to convert str_path to the required format for ChannelAttribute
def str_to_path(str_path):
## creat mapping for channel names
    channel_map = {'A_FTV-DIS':'Awareness Fire TV Display Ads',
    'A_SA': 'Awareness Search Ads',
    'C_OLV': 'Consideration Online Video Ads',
    'C_DSP-DIS': 'Consideration DSP Display Ads',
    'P_DSP-DIS': 'Purchase DSP Display Ads',
    'P_SP': 'Purchase Sponsored Products Ads',
    'P_OO-SA': 'Purchase O&O Search Ads'}

    touchpoints = str_path.split("@")
    arr = [None] * len(touchpoints)
    for tp in touchpoints:
        i, ch = tp.split('&')
        i = int(i) - 1
        arr[i] = channel_map[ch]
    return " > ".join(str(x) for x in arr)

## replace path_clean with the format for ChannelAttibute
Data["path_clean"] = Data.str_path.apply(str_to_path)


Data_One = Data[Data['channels_count'] == 1]
Data_TwoMore = Data[Data['channels_count'] != 1]





### ----- ----- ----- ----- -----
### ----- ----- Dash ----- ----- 
### ----- ----- elements ----- ----- 
### ----- ----- ----- ----- -----

#app = Dash(__name__)
app = Dash(prevent_initial_callbacks="initial_duplicate")
server = app.server


header_L = html.Div([
    html.H1(
        children='AdFlow',
        style={
            #'textAlign': 'right',
            'color': colors['header'],
            #'width': '30%'
        }
    ),
    html.Div(
        children='Budget Allocation Analysis for Nintendo on Amazon platform', 
        style={
            'color': colors['text'], 
            #'width': '70%' 
        }
    ),
    html.Br(),
],style={'width': '40%'})


header_R = html.Div([
    ## filter Number of Channel in the paths
    html.Div([
        html.Div('Number of Channels in the Path'),
        dcc.Dropdown(
            options={
                'full':'Full Set',
                'One':'1 Channel only',
                'Two':'>2 Channels',
                #'custom':'Custom',
                },
            value='full', 
            id = 'filter_channel'
        ), 
        # dcc.Checklist(
        #     options=unique_channel_cnt,
        #     value=unique_channel_cnt,
        #     inline = True, 
        #     id = 'filter_channel_cnt',
        #     #style={'display': 'flex', 'flexDirection': 'row'}
        # ),
        #dcc.Store(id='Data_filtered_ch_cnt')
    ],style={})
])

header = html.Div(
    children=[header_L, header_R],
    style={'display': 'flex', 'flexDirection': 'row'}
)


### ----- ----- ----- -----
### ----- layout tabs -----
### ----- ----- ----- -----

## tab for overall summary
Tab_summary = html.Div(
    id = 'tab-summary',
    children = [
        html.Div(
            id = 'total_overview', 
            children=[dcc.Graph(id = 'fig_conv_count')],
            style={'border':"2px black solid",'border-radius': '10px', 
                   #'width': '300px'
                   }
        ),
        html.Div(
            id = 'path_overview', 
            children = [
                dcc.Graph(id = 'fig_group_channel_cnt', 
                          style={ 'height':'800px' }#'width':'1024px'}
                          ),
            ]
        ), 
    ], 
    #style={'display': 'flex',  'flexDirection': 'row'}, 
)






## Tab for analysis by first/last touch
## see call back function below
# F_L_filter = html.Div([
#     dcc.RadioItems(
#         options = ['First Touch', 'Last Touch'], 
#         value = 'First Touch', 
#         id = 'Radio-First_Last'
#     ),
#     dcc.Store(id='intermediate-value')
# ])

F_L_bar_chart = html.Div([
    dcc.Graph( id = 'fig-first_last_count', style={ 'height':'700px', 'width':'1024px' })
])


Tab_touch = html.Div(
    children= [#F_L_filter, 
               F_L_bar_chart], 
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
    dcc.Graph( id = 'fig-Sankey', style={'height':'700px', 'width':'1024px'})
], style={'display': 'flex', 'flexDirection': 'row'}
)


## Tab for model output
Tab_model = html.Div([
    dcc.Graph(id='fig-model', style={'height':'700px', 'width':'1024px'})
])



### ----- ----- ----- -----
### ----- Final Layout -----
### ----- ----- ----- -----

app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
    header,
    dcc.Tabs([
        dcc.Tab(label="Summary", children= Tab_summary), 
        dcc.Tab(label="Flow Sankey", children= Tab_Sankey),
        dcc.Tab(label="Touch Points Analysis", children= Tab_touch),
        dcc.Tab(label="Conversions in the models", children=Tab_model)
    ])
])



### ----- ----- ----- ----- ----- ----- ----- -----
### ----- All call backs functions below -----
### ----- ----- ----- ----- ----- ----- ----- -----


## Channel count filtering
@callback(
    #Output('filter_channel','value'),
    Output('filter_channel_cnt','value'),
    Input('filter_channel','value'),
    Input('filter_channel_cnt','value')
)
def sync_channel_filters(filter_ch): #, filter_ch_cnt):
    ctx = callback_context
    input_id = ctx.triggered[0]["prop_id"].split(".")[0]
    #print(input_id)
    if input_id == 'filter_channel':
        if filter_ch == 'full':
            filter_ch_cnt = unique_channel_cnt
        elif filter_ch == 'One':
            filter_ch_cnt = [unique_channel_cnt[0]]
        elif filter_ch == 'Two':
            filter_ch_cnt = unique_channel_cnt[1:]
    # else:
    #     if set(filter_ch_cnt) == set(unique_channel_cnt):
    #         filter_ch = 'full'
    #     elif set(filter_ch_cnt) == set(unique_channel_cnt[0]):
    #         filter_ch = 'One'
    #     elif set(filter_ch_cnt) == set(unique_channel_cnt[1:]):
    #         filter_ch = 'Two'
    #     else:
    #         filter_ch = 'custom'

    #return filter_ch, filter_ch_cnt
    return filter_ch_cnt


# ## Data filtered by Channel cnt
# @callback(
#     Output('Data_filtered_ch_cnt', 'data'),
#     Input('filter_channel', 'value')
# )
# def Data_by_ChannelCnt(filter_ch):
#     if filter_ch == 'full':
#         return Data.to_json()
#     elif filter_ch == 'Two':
#         df = Data[Data['channels_count'].isin(unique_channel_cnt[1:])]
#         return df.to_json()



# ## Pivot First/Last Touch count, group by Channel
# @callback(
#     Output('intermediate-value', 'data'),
#     Input('Radio-First_Last', 'value')
# )
# def Count_by_Touch(value):
#     touch = 'first_touch' if value == 'First Touch' else 'last_touch'
#     stat_data = Data.groupby(touch).agg(
#         path_count = pd.NamedAgg(column='path_id', aggfunc='count'),
#         conversion = pd.NamedAgg(column='converters', aggfunc='sum'),
#         non_conversion = pd.NamedAgg(column='nonconverters', aggfunc="sum"))
#     stat_data['conversion_pct'] = round(stat_data.conversion/(stat_data.conversion + stat_data.non_conversion) *100, 3)
#     stat_data['non_conversion_pct'] = round(stat_data.non_conversion/(stat_data.conversion + stat_data.non_conversion)*100, 3)
#     stat_data = stat_data.reset_index().rename(columns={touch: 'channel'})
#     return stat_data.to_json()



# @callback(
#     Output('fig-first_last_count', 'figure'),
#     Input('intermediate-value', 'data'),
#     Input('Radio-First_Last', 'value')
# )
# def update_count_fig(data, touch):
#     dff = pd.read_json(data)
#     fig = px.bar(dff, 
#                  x=['non_conversion','conversion'], 
#                  y='channel', 
#                  title='Count of conversion by '+touch, 
#                  text_auto= ".2s",
#                  orientation='h')
    
#     fig.update_yaxes(title=None)
#     fig.update_xaxes(title=None, showticklabels=False)
#     fig.update_layout(
#         margin=dict(l=20, r=20, t=50, b=20),
#         paper_bgcolor=colors['background'] ,
#         legend = dict(orientation="h",
#                       yanchor="bottom", y=1.0,
#                       xanchor="right", x=1.0, 
#                       title = None)
#     )
#     return fig




@app.callback(
    Output('fig-first_last_count', 'figure'),
    Input('filter_channel', 'value'),
)
def Update_first_Last_graph(filtered_data):
    def stat(data, touch):
        stat_data = data.groupby(touch).agg(
            conversion = pd.NamedAgg(column='converters', aggfunc='sum'),
            non_conversion = pd.NamedAgg(column='nonconverters', aggfunc="sum")
        )
        stat_data['conversion_pct'] = stat_data.conversion/(stat_data.conversion + stat_data.non_conversion) *100
        stat_data['non_conversion_pct'] = stat_data.non_conversion/(stat_data.conversion + stat_data.non_conversion)*100
        return stat_data.reset_index().rename(columns={touch: 'channel'}).sort_values('conversion')
    
    data = Data_One if filtered_data == 'One' else Data_TwoMore if filtered_data == 'Two' else Data
    dff = stat(data, 'first_touch')
    dff_l = stat(data, 'last_touch')

    fig = make_subplots(rows=1, cols=2, specs=[[{},{}]], shared_xaxes = True, shared_yaxes = False, vertical_spacing=0.001)
    fig.append_trace(
        go.Bar(x=dff_l.conversion, y=dff_l.channel, orientation='h', 
               text=dff_l.conversion, insidetextanchor="end",
               marker=dict(color='rgba(50, 171, 96, 0.6)',line=dict(color='rgba(50, 171, 96, 0.6)', width=1),),
               name='Last Touch -- count of conversion', legend="legend2"),
        1, 1
    )
    fig.append_trace(
        go.Bar(x=dff.conversion, y=dff.channel, orientation='h', 
               text=dff.conversion, insidetextanchor="end",
               marker=dict(color='rgba(128, 0, 128, 0.6)',line=dict(color='rgba(128, 0, 128, 0.6)', width=1),),
               name='First Touch -- count of conversion'),
        1, 1
    )

    fig.append_trace(
            go.Scatter(x=dff_l.conversion_pct, y = dff_l.channel, orientation='h',
                    mode='lines+markers+text', 
                    text=dff_l.conversion_pct, texttemplate='%{text:.2f}%',textposition='top right',
                    line_color='rgb(50, 171, 96)', textfont_color='rgb(50, 171, 96)',
                    name='Last Touch -- conversion rate', legend="legend2"), 
            1, 2
        )
    fig.append_trace(
        go.Scatter(x=dff.conversion_pct, y = dff.channel, orientation='h',
                   mode='lines+markers+text', 
                   text=dff.conversion_pct, texttemplate='%{text:.2f}%',textposition='bottom right',
                   line_color='rgb(128, 0, 128)', textfont_color='rgb(128, 0, 128)',
                   name='First Touch -- conversion rate'), 
        1, 2
    )
    
    add_title = "(Paths with only one channel)" if filtered_data == 'One' else "(Paths with >2 channels)" \
        if filtered_data == 'Two' else "(Full dataset)"

    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        title='What is the Conversions by First-/Last- Touch?<br>' + add_title , 
        yaxis = dict(showgrid=False, showline=False, showticklabels=True, domain=[0,0.95],),
        yaxis2 = dict(showgrid=False, showline=True, showticklabels=False, domain=[0,0.95],linecolor='rgba(102, 102, 102, 0.8)',
        linewidth=2,), 
        xaxis = dict(zeroline=False, showline=False, showticklabels=False, showgrid=True, domain=[0,0.42]),
        xaxis2 = dict(zeroline=False, showline=False, showticklabels=False, showgrid=True, domain=[0.47, 1], range = [0, max(dff.conversion_pct)+1]),
        legend = dict(x=0.4, y=1.138, font_size =10), 
        legend2 = dict(x=0.7, y=1.138, font_size =10), 
        paper_bgcolor=colors['plot_bg'], #'rgb(248, 248, 255)',
        plot_bgcolor=colors['plot_bg'], #'rgb(248, 248, 255)',
    )

    return fig









@callback(
    Output('fig_conv_count', 'figure'),
    Input('filter_channel', 'value')
)
def update_pie_fig(filtered_data):
    def create_pie(val, name, title):
        fig = go.Figure(data=[go.Pie(labels=name, 
                             values=val, 
                             hole = 0.5,
                             textinfo='label+value+percent', 
                             marker_colors = [conv_colors['conversion'], conv_colors['non-conversion']],)
                    ]
                )
        fig.update_layout(
            title_text = "How many journeys in the dataset? " + title ,
            title_y = 0.95,
            margin=dict(l=30, r=30, t=130, b=20), 
            showlegend=False,
            paper_bgcolor=colors['background']
            )
        
        fig.add_annotation(text="Total Journeys", 
                   xref= "paper", yref= "paper",
                   x = 0.5, y = 0.55, showarrow = False, 
                    font=dict(size= 20))
        
        fig.add_annotation(text="{:}".format(val[0]+val[1]),
                           xref= "paper", yref= "paper",
                           x = 0.5, y = 0.45, showarrow = False,
                           font=dict(size= 20))
        return fig
    dff = Data_One if filtered_data == 'One' else Data_TwoMore if filtered_data == 'Two' else Data
    add_title = "(Paths with only one channel)" if filtered_data == 'One' else "(Paths with >2 channels)" \
        if filtered_data == 'Two' else "(Full dataset)"
    fig_conv = create_pie([dff.converters.sum(), dff.nonconverters.sum()], ["Converters","Non Conversters"], add_title)
    return fig_conv


## Graph -- group by channel cnt
@callback(
    Output('fig_group_channel_cnt', 'figure'), 
    Input('filter_channel', 'value')
)
def update_channel_cnt_fig(value):
    df = Data.groupby('channels_count').agg(
        converters = pd.NamedAgg(column='converters', aggfunc='sum'),
        nonconverters = pd.NamedAgg(column='nonconverters', aggfunc="sum"),
        ).reset_index()
    df['conversion_pct'] = df.converters/(df.converters + df.nonconverters) *100
    df['non_conversion_pct'] = df.nonconverters/(df.converters + df.nonconverters)*100

    fig = make_subplots(rows=2, cols=1, specs=[[{"type":"scatter"}], [{"type":"bar"}]],
                    shared_xaxes=True, vertical_spacing=0.03,
                    row_heights=[0.25, 0.75])

    fig.add_trace(
        go.Scatter(x = df.channels_count, y = df.conversion_pct, text=df.conversion_pct,
                mode='lines+markers+text', texttemplate='%{text:.2f}%',textposition='top right',
                marker=dict(color=conv_colors['conversion']),
                showlegend=False), 
        row = 1, col = 1
    )

    fig.add_trace(
        go.Bar(x=df.channels_count, y=df.converters, 
            text=df.converters, texttemplate='%{text:.2s}',
            marker=dict(color=conv_colors['conversion']),
            name='conversion'), 
        row = 2, col = 1
    )
    fig.add_trace(
        go.Bar(x=df.channels_count, y=df.nonconverters,
            text=df.nonconverters, texttemplate='%{text:.2s}',
            marker=dict(color=conv_colors['non-conversion']),
            name='non-conversion'), 
        row = 2, col = 1
    )

    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20),
                    yaxis = dict(showgrid=False, showline=False, showticklabels=False, zeroline=False,
                                title = 'conversion rate', range = [-.1,2]),
                    yaxis2 = dict(showgrid=True, showline=False, showticklabels=False, 
                                    title = 'Count of conversion'),
                    xaxis = dict(showgrid=False, showline=False, ),
                    xaxis2 = dict(showgrid=False, showline=False, 
                                    type='category',title = 'Number of Channels in the Path'),
                    legend = dict(x = 1, y = 0.75), 
                    plot_bgcolor= colors['plot_bg'], #'rgb(248, 248, 255)',
                    title='What is the conversion rate per numbers of channel in the path?',
                    #font=dict(size=18),
                    )
    
    return fig


## Sankey
@app.callback(
    Output('fig-Sankey', 'figure'),
    Input('filter_channel', 'value'),
    Input('filter-First', 'value'), 
    Input('filter-Last', 'value'),
    Input('filter-convert', 'value')
)
def update_sankey(filtered_data, First, Last, conv):
    dff = Data_One if filtered_data == 'One' else Data_TwoMore if filtered_data == 'Two' else Data
    df = dff.groupby(['first_touch','last_touch']).agg(
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
            #pad = 15,
            #thickness = 20,
            #line = dict(color = "black", width = 0.5),
            label = [*node,*node],
            #color = "blue"
            ),
        link = dict(
        source = df.first_touch, 
        target = [x + len(node) for x in df.last_touch],
        value = df.conv if conv == 'Converters' else df.nonconv if conv == 'Non Converters' else df.cnt
    ))])

    add_title = "(Paths with only one channel)" if filtered_data == 'One' else "(Paths with >2 channels)" \
        if filtered_data == 'Two' else "(Full dataset)"
    fig.update_layout(title_text= conv + " From First Touch to Last Touch " + add_title)
    
    return fig



@app.callback(
    Output('fig-model', 'figure'),
    Input('filter_channel', 'value'),
)
def plot_model_conv(filtered_data):
    def runModel(Data):
        #ESTIMATE HEURISTIC MODELS (first-/last-/linear- touch models)
        H = heuristic_models(Data,"path_clean","converters",
                            #var_value = "total_conv_values",
                            flg_adv = False)

        #ESTIMATE MARKOV MODEL
        Auto_M = auto_markov_model(Data,
                                "path_clean",
                                "converters",
                                #var_value = "total_conv_values",
                                var_null = "nonconverters",
                                out_more = True,
                                flg_adv = False)
        
        # COMBINE HEURITSTIC & MARKOV
        R = pd.merge(H,Auto_M['result'],on="channel_name",how="inner")
        R.columns=["channel","first_touch","last_touch","linear_touch","markov_model"]
        R = R.sort_values('markov_model', ascending=True)

        # ESTIMATE TRANSITION MATRIX in ORDER = 1
        T = transition_matrix(Data, "path_clean", "converters", var_null = "nonconverters", flg_adv = False)

        return R, Auto_M['removal_effects'].sort_values('removal_effect'), Auto_M['transition_matrix'], T

    add_title = "(Paths with only one channel)" if filtered_data == 'One' else "(Paths with >2 channels)" \
        if filtered_data == 'Two' else "(Full dataset)"
    
    df = Data_One if filtered_data == 'One' else Data_TwoMore if filtered_data == 'Two' else Data
    df, df_RE, df_TM , df_TM1 = runModel(df)

    fig = go.Figure()
    for m in ["markov_model","linear_touch","last_touch","first_touch"]:
        fig.add_trace(
            go.Bar(x = df[m], y = df['channel'], orientation='h', 
                   text = df[m], insidetextanchor="end", texttemplate='%{text:.3s}',
                   marker=dict(color=model_colors[m]),
                   name = m),
        )
    fig.update_yaxes(title=None)
    fig.update_xaxes(title=None, showticklabels=False)
    fig.update_layout(
        margin=dict(l=20, r=20, t=70, b=20),
        title = 'What is the Conversions by touchpoint in each model? ' + add_title, 
        plot_bgcolor= colors['plot_bg'], 
        legend = dict(orientation="h",
                    yanchor="bottom", y=1.0,
                    xanchor="right", x=1.0, 
                    title = None),
        legend_traceorder="reversed",
        #font=dict(size=18),
        )
    return fig



if __name__ == "__main__":
    #app.run_server()
    app.run_server(host="0.0.0.0")