import os
import datetime as dt
import pickle
import gzip
import pprint

import numpy as np
import pandas as pd

import watchcbb.sql as sql
import watchcbb.utils as utils
import watchcbb.efficiency as eff

TODAY = dt.date(2019,11,6)
while TODAY <= dt.date(2020,3,11):
    print(f"Doing date {TODAY}")

    SEASON = TODAY.year if TODAY.month < 6 else TODAY.year+1

    df_games = sql.df_from_query(""" 
        SELECT * FROM game_data
        WHERE "Season"={season} AND "Date"<'{today}'
        ORDER BY "Date"
    """.format(season=SEASON, today=TODAY))

    df_teams = sql.df_from_query("""
        SELECT * from teams
        WHERE year_start<={season} AND year_end>={season}
    """.format(season=SEASON))

    df_preseason = sql.df_from_query("""
        SELECT * from preseason_predictions
        WHERE year={season}
    """.format(season=SEASON))

    season_stats_dict = utils.compute_season_stats(df_games, df_preseason=df_preseason, force_all_teams=True, df_teams=df_teams)
    season_stats_df = utils.stats_dict_to_df(season_stats_dict)
    utils.add_advanced_stats(season_stats_df)
    season_stats_dict = utils.stats_df_to_dict(season_stats_df)

    # convergence parameter
    p = 0.9 + 0.1*min(1000,df_games.shape[0])/1000
    # preseason blend fraction
    preseason_blend = max(0.0, 1 - df_games.shape[0] / 5400.)**2.6
    eff.compute_efficiency_ratings(season_stats_dict, conv_param=p, preseason_blend=preseason_blend)
    season_stats_df = utils.stats_dict_to_df(season_stats_dict)

    # print(season_stats_df.columns)
    # pprint.PrettyPrinter(indent=4).pprint(season_stats_dict[SEASON]['purdue'])
    # print(season_stats_df.sort_values("Tneteff", ascending=False)[["team_id","CompositeRating","Tneteff"]].head(20))
    # break
 
    with gzip.open('../data/season_stats/{0}.pkl.gz'.format(TODAY), 'wb') as fid:
        pickle.dump((season_stats_dict, season_stats_df), fid, protocol=-1)

    TODAY += dt.timedelta(1)
