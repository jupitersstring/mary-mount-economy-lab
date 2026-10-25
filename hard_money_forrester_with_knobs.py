#!/usr/bin/env python3
# Copyright (c) 2026 the repository owner. All rights reserved. See LICENSE.
"""Run with python3 hard_money_forrester_with_knobs.py. No installation needed.

The historical filename is retained for convenience; this revised institutional
model is an accommodating bank-credit economy, not a gold/crypto reserve model.
Edit KNOBS here, use the browser controls, or pass a saved --case JSON file.
"""
import argparse
import csv
import io
import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import data_adapter
import model
import laboratory
import archetypes
import finance

ROOT=Path(__file__).resolve().parent
KNOBS=dict(model.DEFAULTS)  # Every baseline parameter is documented in model.SCHEMA.
EXPERIMENT=[dict(parameter='government_share',amount=.02,start=2,end=5,shape='pulse')]
SCENARIO_KNOBS=None
ISSUER_KNOBS=None


def snapshot():
    path=ROOT/'data/fred_snapshot.json'
    return json.loads(path.read_text()) if path.exists() else None


def bootstrap():
    return dict(schema=model.SCHEMA,defaults=KNOBS,experiment=EXPERIMENT,
                scenario_parameters=SCENARIO_KNOBS or KNOBS,
                result=laboratory.analyse(KNOBS,EXPERIMENT,ISSUER_KNOBS,SCENARIO_KNOBS),data=snapshot(),catalogue=laboratory.catalogue())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def reply(self, status, value, content_type='application/json; charset=utf-8'):
        body=value if isinstance(value,(bytes,bytearray)) else json.dumps(value,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers();self.wfile.write(body)

    def safe_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.safe_host():return self.reply(403,dict(error='Use the loopback URL printed by the launcher.'))
        path=urlsplit(self.path).path
        if path=='/api/bootstrap':return self.reply(200,bootstrap())
        allowed={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css',
                 '/theory.html':'theory.html','/guide.html':'guide.html','/template.csv':'data/template.csv',
                 '/verification.html':'verification.html','/verification.json':'verification.json',
                 '/LICENSE':'LICENSE','/permissions.html':'permissions.html','/provenance.json':'provenance.json','/data/template.csv':'data/template.csv',
                 '/research.html':'research.html','/research.css':'research.css','/research.js':'research.js',
                 '/prototypes.html':'prototypes.html','/methods.html':'methods.html','/experiments.html':'experiments.html',
                 '/issuer-template.json':'data/issuer-template.json',
                 '/initial.js':'initial.js','/data/fred_snapshot.json':'data/fred_snapshot.json'}
        if path not in allowed:return self.reply(404,dict(error='Page not found.'))
        file=ROOT/allowed[path]
        if not file.is_file():return self.reply(404,dict(error='File not found.'))
        ctype=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        self.reply(200,file.read_bytes(),ctype+('; charset=utf-8' if ctype.startswith(('text/','application/javascript')) else ''))

    def do_POST(self):
        if not self.safe_host():return self.reply(403,dict(error='Invalid host.'))
        origin=self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
            return self.reply(403,dict(error='Use the local app to submit requests.'))
        try:
            if not self.headers.get('Content-Type','').startswith('application/json'):
                raise ValueError('Use a JSON request.')
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=1_000_000:raise ValueError('Request must be between 1 byte and 1 MB.')
            obj=json.loads(self.rfile.read(length))
            if not isinstance(obj,dict):raise ValueError('Request must be an object.')
            path=urlsplit(self.path).path
            if path=='/api/run':
                out=laboratory.analyse(obj.get('parameters',{}),obj.get('shocks',[]),obj.get('issuer'),obj.get('scenario_parameters'))
            elif path=='/api/archetype':
                out=archetypes.blend(obj.get('parameters',{}),obj.get('id','reference'),obj.get('strength',1))
            elif path=='/api/import-csv':
                out=data_adapter.parse_csv(obj.get('csv',''))
            elif path=='/api/refresh':
                out=data_adapter.refresh(ROOT/'data/fred_snapshot.json')
            else:return self.reply(404,dict(error='Unknown action.'))
            self.reply(200,out)
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            self.reply(400,dict(error=str(exc)))
        except Exception as exc:
            self.reply(503,dict(error='Data service unavailable ('+type(exc).__name__+'). The saved snapshot has been retained.'))


def main():
    global SCENARIO_KNOBS,ISSUER_KNOBS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--case',type=Path,help='Load a saved case before starting, or export it with --csv.')
    parser.add_argument('--csv',type=Path,help='Export baseline and scenario results to this file and exit.')
    parser.add_argument('--refresh-data',action='store_true',help='Refresh the observed-data snapshot and exit.')
    args=parser.parse_args()
    if args.refresh_data:
        data=data_adapter.refresh(ROOT/'data/fred_snapshot.json')
        print('Saved public-data snapshot:',data['retrieved_at']);return
    if args.case:
        case=json.loads(args.case.read_text())
        KNOBS.update(model.validate(case['parameters']))
        SCENARIO_KNOBS=model.validate(case.get('scenario_parameters',KNOBS))
        ISSUER_KNOBS=finance.validate(case.get('issuer'))
        EXPERIMENT[:]=model.validate_shocks(case.get('shocks',[]),SCENARIO_KNOBS)
    if args.csv:
        result=laboratory.analyse(KNOBS,EXPERIMENT,ISSUER_KNOBS,SCENARIO_KNOBS)
        with args.csv.open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=['case']+list(result['baseline']['rows'][0]))
            writer.writeheader()
            for case in ('baseline','scenario'):
                for row in result[case]['rows']:writer.writerow(dict(case=case,**row))
        print('Saved',args.csv);return
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url=f'http://127.0.0.1:{server.server_port}'
    print('Mary Mount Economy Lab:',url,flush=True)
    print('Stop with Ctrl+C. The model runs locally; data refresh is optional.',flush=True)
    if not args.no_browser:threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
