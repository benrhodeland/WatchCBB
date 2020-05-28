import datetime as dt

import urllib3
from bs4 import BeautifulSoup

import numpy as np
import pandas as pd

def get_html(url):
    """Use urllib3 to retrieve the html source of a given url"""

    http = urllib3.PoolManager()
    r = http.request('GET', url)
    data = r.data
    r.release_conn()
    return data

class SportsRefScrape:
    """Class to perform various web-scraping routines from sports-reference.com/cbb"""

    def __init__(self):
        pass

    def get_gid(self,date,t1,t2):
        """ Return unique game id, with date and alphabetized teams, like 2020-02-15_indiana_purdue" """
        tnames = sorted([t1, t2])
        return "{0}_{1}_{2}".format(date,tnames[0],tnames[1])


    def get_team_list(self, season=2020):
        """ Return a list of all teams in D-I for a given season """

        teams_url = f"http://www.sports-reference.com/cbb/seasons/{season}-school-stats.html"
        teams_html = get_html(teams_url)
        teams_soup = BeautifulSoup(teams_html, "html.parser")
        teams = []
        table = teams_soup.find("table", id="basic_school_stats").find("tbody")
        for td in table.find_all("td", {"data-stat":"school_name"}):
            team = td.find("a")["href"].split("/")[3]
            teams.append(team)

        return teams


    def get_game_data(self, season, fout=None, overwrite=False, teams=None, startdate=None, enddate=None, verbose=False):
        """Retrieve individual game statistics for a set of teams in a given season
        
        Parameters:
        season: year of the season (i.e. 2020 for 2019-20 season)
        fout: file to write output CSV to (None to not write to file)
        overwrite: True to overwrite file, False to append to it (taking care to avoid duplicates)
        teams: list of team IDs (from sports-reference) to retrive games for.
               If None, use all teams in D-I for the given season
        startdate: date to start retrieving games, defaults to beginning of season
        enddate: date to end retrieving games, defaults to full season
        verbose: print extra info

        Returns: list of comma-separated strings, as would be written into the lines of a CSV
        """

        if teams==None:
            teams = self.get_team_list(season)

        gids = {}
        rows = {}

        # if we want to update the game file, record everything in the old file
        if fout is not None and overwrite==False:
            for line in open(fout).readlines()[1:]:
                sp = line.strip().split(",")
                date = sp[1]
                gid = self.get_gid(date,sp[3], sp[5])
                if date not in gids.keys():
                    gids[date] = []
                    rows[date] = []
                rows[date].append(line)
                gids[date].append(gid)

        stats = ["pts","fg","fga","fg3","fg3a","ft","fta","orb","trb","ast","stl","blk","tov","pf"]
        for team in teams:
            if verbose:
                print("Getting games for "+team+"...")

            url = f"http://www.sports-reference.com/cbb/schools/{team}/{season}-gamelogs.html"
            html = get_html(url)
            soup = BeautifulSoup(html, "html.parser")

            # this page only for "game type" (reg season, conf tourney, etc.) If before March, guaranteed Reg Season
            if enddate==None or enddate.month >= 2:
                url2 = "http://www.sports-reference.com/cbb/schools/{0}/{1}-schedule.html".format(team,season)
                html2 = get_html(url2)
                soup2 = BeautifulSoup(html2, "html.parser")

            table = soup.find("table", id="sgl-basic").find("tbody")
            for tr in table.find_all("tr"):
                if tr.get("id") == None:
                    continue

                date = tr.find("td", {"data-stat":"date_game"})
                if date.find("a") != None:
                    date = date.find("a").string
                else:
                    continue
                opp = tr.find("td", {"data-stat":"opp_id"})

                if startdate!=None and startdate > dt.date(*[int(x) for x in date.split("-")]):
                    continue 

                if enddate!=None and enddate < dt.date(*[int(x) for x in date.split("-")]):
                    continue 

                if opp.find("a")==None:
                    continue
                opp = opp.find("a")["href"].split("/")[3]
                gid = self.get_gid(date, team, opp)
                datem1day = str(dt.date(*[int(x) for x in date.split("-")]) - dt.timedelta(1))
                gidm1day = self.get_gid(datem1day, team, opp)
                if date not in gids.keys():
                    gids[date] = []
                    rows[date] = []                
                if gid in gids[date] or (datem1day in gids.keys() and gidm1day in gids[datem1day]):
                    continue
                else:
                    gids[date].append(gid)

                if enddate==None or enddate.month >= 2:
                    gtype = soup2.find("td",{"csk":date}).find_parent("tr").find("td",{"data-stat":"game_type"}).string
                else:
                    gtype = "REG"
                if gtype == "REG":
                    gtype = "RG"
                if gtype == "CTOURN":
                    gtype = "CT"

                loc = tr.find("td", {"data-stat":"game_location"}).string
                if loc==None:    loc="H"
                elif loc=="@": loc="A"
                elif loc=="N": loc="N"
                else:
                    raise Exception(loc)

                numot = tr.find("td", {"data-stat":"game_result"})
                if numot.find("small") != None:
                    numot = int(numot.find("small").string.split("(")[1].split()[0])
                else:
                    numot = 0

                statdict = {}
                opp_statdict = {}
                getint = lambda x: (0 if x is None else int(x))
                for stat in stats:
                    statdict[stat] = getint(tr.find("td",{"data-stat":stat}).string)
                    opp_statdict[stat] = getint(tr.find("td",{"data-stat":"opp_"+stat}).string)

                if statdict["pts"] > opp_statdict["pts"]:
                    wd, ld = statdict, opp_statdict
                    wteam, lteam = team, opp
                else:
                    wd, ld = opp_statdict, statdict
                    wteam, lteam = opp, team
                    if loc=="H":   loc="A"
                    elif loc=="A": loc="H"

                string = "{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},\
{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34}\n".format(
    season,date,gtype,wteam,wd["pts"],lteam,ld["pts"],loc,numot,
    wd["fg"],wd["fga"],wd["fg3"],wd["fg3a"],wd["ft"],wd["fta"],wd["orb"],wd["trb"]-wd["orb"],wd["ast"],wd["tov"],wd["stl"],wd["blk"],wd["pf"],
    ld["fg"],ld["fga"],ld["fg3"],ld["fg3a"],ld["ft"],ld["fta"],ld["orb"],ld["trb"]-ld["orb"],ld["ast"],ld["tov"],ld["stl"],ld["blk"],ld["pf"])

                rows[date].append(string)

        if fout:
            fout = open(fout, 'w')
            fout.write("Season,DayNum,Type,WTeamID,WScore,LTeamID,LScore,WLoc,NumOT,WFGM,WFGA,WFGM3,WFGA3,WFTM,WFTA,WOR,WDR,\
WAst,WTO,WStl,WBlk,WPF,LFGM,LFGA,LFGM3,LFGA3,LFTM,LFTA,LOR,LDR,LAst,LTO,LStl,LBlk,LPF\n")
            for date in sorted(gids.keys()):
                for s in rows[date]:
                    fout.write(s)
            fout.close()

        return rows




if __name__=="__main__":
    
    sr = SportsRefScrape()
    sr.get_game_data(2020, fout="../scratch/test.csv", overwrite=True, teams=['purdue'], verbose=True)
