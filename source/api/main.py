from fastapi import FastAPI, Response
from fastapi.responses import PlainTextResponse
from starlette.responses import StreamingResponse
from utils.api.servers import servers
from api.filter import build_query
from sqlalchemy.orm import aliased
from sqlalchemy import and_, not_
from utils.database import *

import utils.collections as collections
import utils.postgres as postgres
import datetime
import uvicorn


sort_desc = desc
sort_asc = asc

app = FastAPI()

class TypeEnum(str, Enum):
    pp = "pp"
    score = "score"
    first_places = "1s"
    clears = "clears"

class FirstPlacesEnum(str, Enum):
    all = "all"
    new = "new"
    lost = "lost"

class ScoreSortEnum(str, Enum):
    beatmap_id = "beatmap_id"
    score_id = "score_id"
    accuracy = "accuracy"
    mods = "mods"
    pp = "pp"
    score = "score"
    combo = "combo"
    rank = "rank"
    date = "date"

class BeatmapSortEnum(str, Enum):
    artist = "artist"
    title = "title"
    version = "version"
    mapper = "mapper"
    stars_nm = "stars_nm"
    length = "length"
    ranked_status = "ranked_status"
    approved_date = "approved_date"
    last_checked = "last_checked"

class DownloadEnum(str, Enum):
    csv = "csv"
    collection = "collection"

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/leaderboard/user")
async def get_user_leaderboard(server="akatsuki", mode:int=0, relax:int=0, page:int=1, length:int=100, type: str = TypeEnum.pp):
    length = min(100, length)
    orders = {'pp': 'global_rank', 'score': 'global_score_rank'}
    order = orders['pp']
    if type in orders:
        order = orders[type]
    users = []
    with postgres.instance.managed_session() as session:
        if order == 'global_rank' or order == 'global_score_rank':
            model = DBLiveUser if order == 'global_rank' else DBLiveUserScore
            query = session.query(model).filter(model.server == server, model.mode == mode, 
                                                     model.relax == relax).order_by(
                                                         model.global_rank)
            for stats in query.offset((page-1)*length).limit(length).all():
                users.append(stats)
        return {'total': query.count(), 'users': users}

@app.get("/leaderboard/user_extra")
async def get_user_statistics(server="akatsuki", date=str(datetime.datetime.now().date()), mode:int=0, relax:int=0, page:int=1, length:int=100, type: str = TypeEnum.clears):
    length = min(100, length)
    orders = {
        'pp': 'global_rank', 
        'score': 'global_score_rank', 
        'total_score': 'total_score DESC', 
        'clears': 'clears DESC', 
        '1s': 'first_places DESC', 
        'xh_count': 'xh_count DESC', 
        'x_count': 'x_count DESC', 
        'sh_count': 'sh_count DESC', 
        's_count': 's_count DESC',
        'a_count': 'a_count DESC',
        'b_count': 'b_count DESC',
        'c_count': 'c_count DESC',
        'd_count': 'd_count DESC',
    }
    order = orders['pp']
    if type in orders:
        order = orders[type]
    users = []
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    with postgres.instance.managed_session() as session:
        query = session.query(DBStats).filter(DBStats.server == server, DBStats.mode == mode,
                                                   DBStats.relax == relax, DBStats.date == date).order_by(
                                                       text(order))
        for stats in query.offset((page-1)*length).limit(length).all():
            users.append(stats)
        return {'total': query.count(), 'users': users}

@app.get("/leaderboard/clan")
async def get_clan_leaderboard(server="akatsuki", mode:int=0, relax:int=0, date=str(datetime.datetime.now().date()), page:int=1, length:int=100, type: str = TypeEnum.pp):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    length = min(100, length)
    clans = []
    with postgres.instance.managed_session() as session:
        orders = {'pp': 'global_rank', '1s': 'global_rank_1s', 'score': 'ranked_score DESC', 'total_score': 'total_score DESC', 'play_count': 'play_count DESC'}
        order = orders['pp']
        if type in orders:
            order = orders[type]
        query = session.query(DBClanStats).filter(DBClanStats.server == server, DBClanStats.mode == mode, 
                                                     DBClanStats.relax == relax, DBClanStats.date == date).order_by(
                                                         text(order))
        if order == "global_rank_1s":
            query = query.filter(DBClanStats.global_rank_1s > 0)
        for stats in query.offset((page-1)*length).limit(length).all():
            clans.append(stats)
        return {'total': query.count(), 'clans': clans}


@app.get("/user/stats")
async def get_user(user_id:int, server="akatsuki", mode:int=0, relax:int=0,date=str(datetime.datetime.now().date())):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    with postgres.instance.managed_session() as session:
        return session.get(DBStats, (user_id, server, mode, relax, date))

@app.get("/user/first_places")
async def get_user_1s(user_id:int, server="akatsuki", mode:int=0, relax:int=0, type=FirstPlacesEnum.all, date=str(datetime.datetime.now().date()), sort: str = ScoreSortEnum.date, desc: bool=True, score_filter: str = "", beatmap_filter: str = "", page:int=1, length:int=100, download_as: str = ""):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    first_places = list()
    yesterday = (date - datetime.timedelta(days=1))
    direction = sort_desc if desc else sort_asc
    with postgres.instance.managed_session() as session:
        query = session.query(DBUserFirstPlace).filter(DBUserFirstPlace.server == server,
                                                            DBUserFirstPlace.user_id == user_id,
                                                            DBUserFirstPlace.mode == mode,
                                                            DBUserFirstPlace.relax == relax,
                                                            DBUserFirstPlace.date == date,
                                                            ).join(DBScore).order_by(direction(getattr(DBScore, sort)))
        if score_filter:
            query = build_query(query, DBScore, score_filter.split(","))
        if beatmap_filter:
            query = build_query(query.join(DBBeatmap), DBBeatmap, beatmap_filter.split(","))
        if type == "all":
            match download_as:
                case DownloadEnum.csv:
                    columns = [c.name for c in DBScore.__table__.columns]
                    csv = "\t".join(columns)+"\n"
                    for first_place in query.all():
                        csv += "\t".join([str(getattr(first_place.score, c)) for c in columns])+"\n"
                    response = Response(content=csv, media_type="text/csv")
                    response.headers["Content-Disposition"] = "attachment; filename=first_places.csv"
                    return response
                case DownloadEnum.collection:
                    beatmaps = list()
                    for first_place in query.all():
                        beatmaps.append(first_place.score.beatmap)
                    response = StreamingResponse(content=collections.generate_collection(beatmaps, "first_places"), 
                                             media_type="application/octet-stream")
                    response.headers["Content-Disposition"] = "attachment; filename=first_places.osdb"
                    return response
                case _:
                    for first_place in query.offset((page-1)*length).limit(length).all():
                        first_places.append(first_place.score)  
                    total = query.count()
                    return {'total': total, 'scores': first_places}
        elif type == "new":
            new = list()
            for first_place in query.all():
                if (old := session.query(DBUserFirstPlace).filter(
                    DBUserFirstPlace.date == yesterday,
                    DBUserFirstPlace.score_id == first_place.score_id
                )).first() is None:
                    new.append(first_place)
            offset = (page-1)*length
            total = len(new)
            if len(new) < offset:
                return {'total': total, 'scores': list()}
            first_places = list()
            for first_place in new[offset:offset+length]:
                first_places.append(first_place.score)  
            return {'total': total, 'scores': first_places}
        elif type == "lost":
            lost = list()
            for first_place in session.query(DBUserFirstPlace).filter(DBUserFirstPlace.server == server,
                                                            DBUserFirstPlace.user_id == user_id,
                                                            DBUserFirstPlace.mode == mode,
                                                            DBUserFirstPlace.relax == relax,
                                                            DBUserFirstPlace.date == yesterday,
                                                            ).all():
                if (new := session.query(DBUserFirstPlace).filter(
                    DBUserFirstPlace.date == date,
                    DBUserFirstPlace.score_id == first_place.score_id
                )).first() is None:
                    lost.append(first_place)
            offset = (page-1)*length
            total = len(lost)
            if len(lost) < offset:
                return {'total': total, 'scores': list()}
            first_places = list()
            for first_place in lost[offset:offset+length]:
                first_places.append(first_place.score)  
            return {'total': total, 'scores': first_places}

@app.get("/user/first_places/all")
async def get_user_1s(server="akatsuki", mode:int=0, relax:int=0, date=str(datetime.datetime.now().date()), sort: str = ScoreSortEnum.date, desc: bool=True, score_filter: str = "", beatmap_filter: str = "", page:int=1, length:int=100, download_as: str = ""):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    first_places = list()
    direction = sort_desc if desc else sort_asc
    with postgres.instance.managed_session() as session:
        query = session.query(DBUserFirstPlace).filter(DBUserFirstPlace.server == server,
                                                            DBUserFirstPlace.mode == mode,
                                                            DBUserFirstPlace.relax == relax,
                                                            DBUserFirstPlace.date == date,
                                                            ).join(DBScore).order_by(direction(getattr(DBScore, sort)))
        if score_filter:
            query = build_query(query, DBScore, score_filter.split(","))
        if beatmap_filter:
            query = build_query(query.join(DBBeatmap), DBBeatmap, beatmap_filter.split(","))
        match download_as:
            case DownloadEnum.csv:
                columns = [c.name for c in DBScore.__table__.columns]
                csv = "\t".join(columns)+"\n"
                for first_place in query.all():
                    csv += "\t".join([str(getattr(first_place.score, c)) for c in columns])+"\n"
                response = Response(content=csv, media_type="text/csv")
                response.headers["Content-Disposition"] = "attachment; filename=first_places.csv"
                return response
            case DownloadEnum.collection:
                beatmaps = list()
                for first_place in query.all():
                    beatmaps.append(first_place.score.beatmap)
                response = StreamingResponse(content=collections.generate_collection(beatmaps, "first_places"), 
                                             media_type="application/octet-stream")
                response.headers["Content-Disposition"] = "attachment; filename=first_places.osdb"
                return response
            case _:
                for first_place in query.offset((page-1)*length).limit(length).all():
                    first_places.append(first_place.score)
                total = query.count()
                return {'total': total, 'scores': first_places}


@app.get("/user/clears")
async def get_user_clears(user_id:int, server="akatsuki", mode:int=0, relax:int=0, date=str(datetime.datetime.now().date()), page:int=1, completed=3, score_filter: str = "", beatmap_filter: str = "", sort: str = ScoreSortEnum.date, desc: bool=True, length:int=100, download_as: str = ""):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    scores = list()
    direction = sort_desc if desc else sort_asc
    with postgres.instance.managed_session() as session:
        query = session.query(DBScore).filter(DBScore.server == server,
                                                            DBScore.user_id == user_id,
                                                            DBScore.mode == mode,
                                                            DBScore.relax == relax,
                                                            DBScore.completed == completed
                                                            ).order_by(direction(getattr(DBScore, sort)))
        if score_filter:
            query = build_query(query, DBScore, score_filter.split(","))
        if beatmap_filter:
            query = build_query(query.join(DBBeatmap), DBBeatmap, beatmap_filter.split(","))
        match download_as:
            case DownloadEnum.csv:
                columns = [c.name for c in DBScore.__table__.columns]
                csv = "\t".join(columns)+"\n"
                for score in query.all():
                    csv += "\t".join([str(getattr(score, c)) for c in columns])+"\n"
                response = Response(content=csv, media_type="text/csv")
                response.headers["Content-Disposition"] = "attachment; filename=first_places.csv"
                return response
            case DownloadEnum.collection:
                beatmaps = list()
                for score in query.all():
                    beatmaps.append(score.beatmap)
                response = StreamingResponse(content=collections.generate_collection(beatmaps, "clears"), 
                                             media_type="application/octet-stream")
                response.headers["Content-Disposition"] = "attachment; filename=clears.osdb"
                return response
            case _:
                for score in query.offset((page-1)*length).limit(length).all():
                    scores.append(session.query(DBScore).filter(DBScore.score_id == score.score_id).first())  
                total = query.count()
                return {'total': total, 'scores': scores}

@app.get("/user/clears/all")
async def get_all_clears( server="akatsuki", mode:int=0, relax:int=0, date=str(datetime.datetime.now().date()), page:int=1, completed=3, score_filter: str = "", beatmap_filter: str = "", sort: str = ScoreSortEnum.date, desc: bool=True, length:int=100, download_as: str = ""):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    scores = list()
    direction = sort_desc if desc else sort_asc
    with postgres.instance.managed_session() as session:
        query = session.query(DBScore).filter(DBScore.server == server,
                                                            DBScore.mode == mode,
                                                            DBScore.relax == relax,
                                                            DBScore.completed == completed
                                                            ).order_by(direction(getattr(DBScore, sort)))
        if score_filter:
            query = build_query(query, DBScore, score_filter.split(","))
        if beatmap_filter:
            query = build_query(query.join(DBBeatmap), DBBeatmap, beatmap_filter.split(","))
        match download_as:
            case DownloadEnum.csv:
                columns = [c.name for c in DBScore.__table__.columns]
                csv = "\t".join(columns)+"\n"
                for score in query.all():
                    csv += "\t".join([str(getattr(score, c)) for c in columns])+"\n"
                response = Response(content=csv, media_type="text/csv")
                response.headers["Content-Disposition"] = "attachment; filename=clears.csv"
                return response
            case DownloadEnum.collection:
                beatmaps = list()
                for score in query.all():
                    beatmaps.append(score.beatmap)
                response = StreamingResponse(content=collections.generate_collection(beatmaps, "clears"), 
                                             media_type="application/octet-stream")
                response.headers["Content-Disposition"] = "attachment; filename=clears.osdb"
                return response
            case _:
                for score in query.offset((page-1)*length).limit(length).all():
                    scores.append(session.query(DBScore).filter(DBScore.score_id == score.score_id).first())  
                total = query.count()
                return {'total': total, 'scores': scores}


@app.get("/user/rank")
async def get_user_leaderboard(user_id: int, server="akatsuki", date=str(datetime.datetime.now().date()), mode:int=0, relax:int=0, type: str = TypeEnum.pp):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    with postgres.instance.managed_session() as session:
        if date != datetime.datetime.now().date():
            if (stats := session.get(DBStats, (user_id, server, mode, relax, date))) is not None:
                if type == "pp":
                    return {'global_rank': stats.global_rank, 'country_rank': stats.country_rank}
                else:
                    return {'global_rank': stats.global_score_rank, 'country_rank': stats.country_score_rank}
        else:
            model = DBLiveUser if type == 'pp' else DBLiveUserScore
            if (stats := session.get(model, (server, user_id, mode, relax))) is not None:
                return {'global_rank': stats.global_rank, 'country_rank': stats.country_rank}
        return {'global_rank': -1, 'country_rank': -1}

@app.get("/user/completion/stats")
async def get_user_stars_completion(user_id: int, server: str = "akatsuki", mode: int = 0, relax: int = 0):
    set = None
    for srv in servers:
        if srv.server_name == server:
            set = srv.beatmap_sets[0]
            break
    if not set:
        return
    import time
    with postgres.instance.managed_session() as session:
        ar = {}
        cs = {}
        od = {}
        sr = {}
        for x in range(12):
            ar[x] = 0
            cs[x] = 0
            od[x] = 0
            sr[x] = 0
            
        for score in session.query(DBScore).filter(DBScore.user_id == user_id, 
                                                   DBScore.mode == mode, 
                                                   DBScore.relax == relax, 
                                                   DBScore.server == server
                                                   ).join(DBBeatmap).all():
            ar[min(11, int(score.beatmap.ar))] += 1
            cs[min(11, int(score.beatmap.cs))] += 1
            od[min(11, int(score.beatmap.od))] += 1
            sr[min(11, int(score.beatmap.stars_nm))] += 1
        res = {'stars': [], 'ar': [], 'cs': [], 'od': []}
        if session.query(DBCompletionCache).count() == 0:
            return res
        for x in range(12):
            max_ar = session.get(DBCompletionCache, (f"ar_{set}_{mode}_{x}")).value
            max_cs = session.get(DBCompletionCache, (f"cs_{set}_{mode}_{x}")).value
            max_od = session.get(DBCompletionCache, (f"od_{set}_{mode}_{x}")).value
            max_sr = session.get(DBCompletionCache, (f"stars_{set}_{mode}_{x}")).value
            if x != 11:
                res['stars'].append({'name': f'{x}*', 'completed': sr[x], 'total': max_sr})
                res['ar'].append({'name': f'AR {x}', 'completed': ar[x], 'total': max_ar})
                res['cs'].append({'name': f'CS {x}', 'completed': cs[x], 'total': max_cs})
                res['od'].append({'name': f'OD {x}', 'completed': od[x], 'total': max_od})
            else:
                res['stars'].append({'name': f'{x}*+', 'completed': sr[x], 'total': max_sr})
                res['ar'].append({'name': f'AR {x}+', 'completed': ar[x], 'total': max_ar})
                res['cs'].append({'name': f'CS {x}+', 'completed': cs[x], 'total': max_cs})
                res['od'].append({'name': f'OD {x}+', 'completed': od[x], 'total': max_od})
        return res

@app.get("/user/info")
async def get_user_info(user_id:int, server="akatsuki"):
    with postgres.instance.managed_session() as session:
        return session.get(DBUser, (user_id, server))

@app.get("/user/list")
async def get_user_list(server: str = "akatsuki", desc: bool = True, sort: str = "user_id", length: int = 100, page: int = 1, filter: str = ""):
    direction = sort_desc if desc else sort_asc
    with postgres.instance.managed_session() as session:
        query = session.query(DBUser).filter(DBUser.server == server).order_by(direction(getattr(DBUser, sort)))
        if filter:
            query = build_query(query, DBUser, filter.split(","))
        query = query.offset(((page-1)*length)).limit(length)
        return {'total': query.count(), 'users': [user for user in query.all()]}
            

@app.get("/clan/info")
async def get_clan_info(clan_id:int, server="akatsuki"):
    with postgres.instance.managed_session() as session:
        return session.get(DBClan, (server, clan_id))

@app.get("/clan/members")
async def get_clan_members(clan_id:int, server="akatsuki"):
    members = list()
    with postgres.instance.managed_session() as session:
        for member in session.query(DBUser).filter(DBUser.server == server, DBUser.clan == clan_id).all():
            members.append(member)
        return members

@app.get("/clan/stats")
async def get_clan_stats(clan_id:int, server="akatsuki", mode:int=0, relax:int=0,date=str(datetime.datetime.now().date())):
    date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    with postgres.instance.managed_session() as session:
        return session.get(DBClanStats, (server, clan_id, mode, relax, date))

@app.get("/beatmap")
async def get_beatmap(beatmap_id: int):
    with postgres.instance.managed_session() as session:
        return session.get(DBBeatmap, beatmap_id)

@app.get("/beatmaps/server_sets")
async def get_sets():
    server_list = {}
    for server in servers:
        server_list[server.server_name] = server.beatmap_sets
    return server_list

@app.get("/beatmaps/list")
async def get_beatmaps(page: int = 1, length: int = 100, sort: str = BeatmapSortEnum.title, desc: bool = False, unplayed_by_filter: str = "", beatmap_filter: str = "", download_as: str = ""):
    beatmaps = list()
    direction = sort_desc if desc else sort_asc
    with postgres.instance.managed_session() as session:
        query = session.query(DBBeatmap)
        if beatmap_filter:
            query = build_query(query, DBBeatmap, beatmap_filter.split(","))
        
        if unplayed_by_filter:
            try:
                args = unplayed_by_filter.split(",")
                mode = int(args[0])
                relax = int(args[1])
                user_id = int(args[2])
                server = str(args[3])
            except:
                return PlainTextResponse(status_code=400, content="Invalid unplayed_by_filter syntax! Valid syntax: mode:int,relax:int,user_id:int,server:str")
            
            # Subquery to filter DBScore objects
            subquery = (session.query(DBScore.beatmap_id).filter(
                DBScore.mode == mode,
                DBScore.relax == relax,
                DBScore.server == server,
                DBScore.user_id == user_id
            ).subquery())

            # Black magic
            db_beatmap_alias = aliased(DBBeatmap)
                        
            query = (
                query
                .outerjoin(db_beatmap_alias, DBBeatmap.beatmap_id == db_beatmap_alias.beatmap_id)
                .filter(not_(DBBeatmap.beatmap_id.in_(subquery)))
            )
                
        query = query.order_by(direction(getattr(DBBeatmap, sort)))
        match download_as:
            case DownloadEnum.csv:
                columns = [c.name for c in DBBeatmap.__table__.columns]
                csv = "\t".join(columns)+"\n"
                for beatmap in query.all():
                    csv += "\t".join([str(getattr(beatmap, c)) for c in columns])+"\n"
                response = Response(content=csv, media_type="text/csv")
                response.headers["Content-Disposition"] = "attachment; filename=beatmaps.csv"
                return response
            case DownloadEnum.collection:
                beatmaps = list()
                for beatmap in query.all():
                    beatmaps.append(beatmap)
                response = StreamingResponse(content=collections.generate_collection(beatmaps, "beatmaps"), 
                                             media_type="application/octet-stream")
                response.headers["Content-Disposition"] = "attachment; filename=beatmaps.osdb"
                return response
            case _:
                for beatmap in query.offset((page-1)*length).limit(length):
                    beatmaps.append(beatmap)
                return {'total': query.count(), 'beatmaps': beatmaps}

@app.get("/metrics/requests")
async def get_requests_metrics():
    metrics = list()
    with postgres.instance.managed_session() as session:
        for metric in session.query(DBMetricsRequests).order_by(desc(DBMetricsRequests.requests)).all():
            metrics.append(metric)
    return metrics

def main():
    uvicorn.run(app, host="0.0.0.0", port=4269)