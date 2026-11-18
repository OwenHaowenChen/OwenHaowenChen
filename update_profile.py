"""Render Owen's terminal profile using public GitHub data. Python stdlib only."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
USER = os.environ.get('PROFILE_USERNAME', 'OwenHaowenChen')
TOKEN = os.environ.get('GH_TOKEN')
API = 'https://api.github.com'

def request(path, body=None):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'owen-profile', 'X-GitHub-Api-Version': '2022-11-28'}
    if TOKEN:
        headers['Authorization'] = 'Bearer ' + TOKEN
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(urllib.request.Request(API + path, data=data, headers=headers), timeout=45) as response:
        result = json.load(response)
    if isinstance(result, dict) and result.get('errors'):
        raise RuntimeError('GitHub GraphQL query failed: ' + str(result['errors']))
    return result

def collect():
    user = request('/users/' + USER)
    repos = []
    page = 1
    while True:
        batch = request(f'/users/{USER}/repos?type=owner&per_page=100&page={page}')
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    result = {'created_at': user['created_at'], 'repos': user['public_repos'], 'stars': sum(r['stargazers_count'] for r in repos if not r['fork']), 'followers': user['followers']}
    if not TOKEN:
        raise RuntimeError('GH_TOKEN is required for contribution statistics.')
    query = 'query($login:String!){user(login:$login){contributionsCollection{totalCommitContributions contributionCalendar{totalContributions}}}}'
    contributions = request('/graphql', {'query': query, 'variables': {'login': USER}})['data']['user']['contributionsCollection']
    result['commits'] = contributions['totalCommitContributions']
    result['contributions'] = contributions['contributionCalendar']['totalContributions']
    return result

def render(stats):
    now = dt.datetime.now(dt.timezone.utc)
    created = dt.datetime.fromisoformat(stats['created_at'].replace('Z', '+00:00'))
    days = (now-created).days
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1110" height="640" viewBox="0 0 1110 640" role="img" aria-labelledby="title desc">',
           '<title id="title">Owen Chen | neofetch</title>',
           '<desc id="desc">Monochrome ASCII Patrick portrait, engineering profile, and daily public GitHub statistics.</desc>',
           '<rect width="1110" height="640" rx="18" fill="#161b22"/>',
           '<style>text,tspan{white-space:pre}text{font-family:Menlo,Consolas,"Liberation Mono",monospace;font-weight:400}.key{fill:#ffa657}.value{fill:#a5d6ff}.muted{fill:#616e7f}.text{fill:#c9d1d9}</style>']
    # A single monospace grid keeps all dot leaders and right edges aligned.
    X, CELL, COLS = 414, 9.6, 70
    def text(x,y,value,color='#c9d1d9',size=16):
        svg.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" xml:space="preserve">{html.escape(str(value))}</text>')
    def segments(y,parts):
        count=sum(len(str(value)) for _,value in parts)
        if count>COLS:
            raise ValueError(f'Profile row exceeds {COLS} columns: {parts}')
        nodes=''.join(f'<tspan class="{kind}">{html.escape(str(value))}</tspan>' for kind,value in parts)
        svg.append(f'<text x="{X}" y="{y}" font-size="16" textLength="{count*CELL}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{nodes}</text>')
    def row(index,label,value):
        label+=':'
        value=str(value)
        gap=COLS-len(label)-len(value)
        if gap<3:
            raise ValueError(f'Not enough room for {label}')
        segments(35+index*23, [('key',label),('muted',' '+'.'*(gap-2)+' '),('value',value)])
    def heading(index,label):
        value=label+' '
        y=35+index*23
        text(X,y,label)
        svg.append(f'<path d="M{X+len(value)*CELL} {y-5}H1086" stroke="#c9d1d9" stroke-width="1.2"/>')
    # Render each ASCII row as text rather than hundreds of disconnected pixels.
    art=json.loads((ROOT/'avatar.json').read_text())
    for i,line in enumerate(art):
        length=len(line)*8.4
        svg.append(f'<text x="14" y="{80+i*16.8:.1f}" fill="#c9d1d9" font-size="14" textLength="{length:.2f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{html.escape(line)}</text>')
    # The dotted vertical separator follows the same rhythm as the information.
    for i in range(25):
        text(394,35+i*23,'·','#616e7f')
    heading(0,'owen@stanford')
    row(1,'Name','Haowen (Owen) Chen')
    row(2,'OS','macOS')
    row(3,'Uptime',f'{days} days on GitHub')
    row(4,'Host','Stanford University')
    row(5,'Kernel','MS Environmental Engineering')
    row(6,'Education','ZJU + UIUC / Mechanical Engineering')
    row(7,'IDE','VS Code, Jupyter')
    row(9,'Languages.Programming','Python, MATLAB, R')
    row(10,'Tools.CAD','SolidWorks, Fusion 360, Creo')
    row(11,'Tools.Simulation','ANSYS Fluent, Abaqus')
    row(13,'Focus','Product Design, Thermal Systems')
    row(14,'Hobbies.Software','Robotics, Building Apps')
    row(15,'Hobbies.Hardware','3D Printing, Prototyping')
    row(16,'Side.Quests','Road Trips, National Parks')
    heading(18,'Contact')
    row(19,'GitHub','github.com/OwenHaowenChen')
    row(20,'Project','Focus Flock')
    heading(22,'GitHub Stats / public')
    def num(key):
        value=stats[key]
        return f'{value:,}' if isinstance(value,int) else str(value)
    def pair(index,leftkey,leftval,rightkey,rightval):
        leftlabel=leftkey+':'
        rightlabel=rightkey+':'
        leftgap=33-len(leftlabel)-len(leftval)
        rightgap=34-len(rightlabel)-len(rightval)
        segments(35+index*23,[('key',leftlabel),('muted',' '+'.'*(leftgap-2)+' '),('value',leftval),('text',' | '),('key',rightlabel),('muted',' '+'.'*(rightgap-2)+' '),('value',rightval)])
    pair(23,'Repos',num('repos'),'Stars',num('stars'))
    pair(24,'Commits.365d',num('commits'),'Followers',num('followers'))
    row(25,'Contributions.365d',num('contributions'))
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'

def main():
    stats=collect()
    (ROOT/'profile.svg').write_text(render(stats))
    print('Rendered profile.svg')

if __name__ == '__main__':
    main()
