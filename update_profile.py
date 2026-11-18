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
    age = (now-created).days
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="660" viewBox="0 0 1040 660" role="img" aria-labelledby="title desc">', '<title id="title">Owen Chen | terminal profile</title>', '<desc id="desc">Color ASCII Patrick in a Santa hat beside Owen\'s engineering background and automatically refreshed public GitHub statistics.</desc>', '<rect x="1" y="1" width="1038" height="658" rx="18" fill="#0d1117" stroke="#30363d" stroke-width="2"/>', '<path d="M19 1H1021Q1039 1 1039 19V53H1V19Q1 1 19 1" fill="#161b22"/>']
    def text(x,y,value,size=16,color='#c9d1d9',bold=False):
        weight='700' if bold else '400'
        svg.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Menlo,Consolas,monospace" font-size="{size}" font-weight="{weight}" xml:space="preserve">{html.escape(str(value))}</text>')
    for x,color in [(25,'#ff5f57'),(47,'#febc2e'),(69,'#28c840')]:
        svg.append(f'<circle cx="{x}" cy="27" r="6" fill="{color}"/>')
    text(380,32,'owen@stanford: ~',14,'#8b949e')
    text(30,87,'❯',19,'#7ee787')
    text(54,87,'neofetch --user owen',16,'#c9d1d9')
    art=json.loads((ROOT/'avatar.json').read_text())
    for row_index,row in enumerate(art):
        for col,cell in enumerate(row):
            if cell:
                text(29+col*7.4,115+row_index*11.3,cell[0],12,cell[1],True)
    svg.append('<path d="M378 118V526" stroke="#30363d"/>')
    text(406,137,'owen@stanford',23,'#ff9b94',True)
    text(406,162,'-------------------------------',15,'#484f58')
    fields=[('Name','Haowen (Owen) Chen'),('OS','macOS / engineer mode'),('Host','Stanford University'),('Kernel','Mechanical → Environmental Eng.'),('Uptime',f'{age} days on GitHub'),('Education','ZJU + UIUC → Stanford MS'),('Focus','Product design · Heat transfer'),('Research','Capillary-driven desalination'),('Languages','Python · MATLAB · Arduino'),('Tools','SolidWorks · Fluent · ROS'),('Human','English · Mandarin'),('Side quests','Prototyping · Robotics · Road trips')]
    for i,(label,value) in enumerate(fields):
        y=190+i*26
        text(406,y,label+':',15,'#79c0ff',True)
        text(522,y,value,15)
    for i,color in enumerate(['#ff7b72','#ffa657','#e3b341','#7ee787','#79c0ff','#d2a8ff','#ff9bce','#c9d1d9']):
        svg.append(f'<rect x="{406+i*27}" y="508" width="27" height="16" fill="{color}"/>')
    svg.append('<path d="M28 548H1012" stroke="#30363d"/>')
    metrics=[('PUBLIC REPOS',stats['repos']),('STARS / OWNED',stats['stars']),('COMMITS / 365D',stats['commits']),('CONTRIBS / 365D',stats['contributions'])]
    for i,(label,value) in enumerate(metrics):
        x=32+i*249
        text(x,576,label,11,'#8b949e')
        text(x,609,f'{value:,}' if isinstance(value,int) else value,26,'#7ee787',True)
    text(32,640,'public GitHub activity · refreshed daily',11,'#8b949e')
    text(690,640,'updated '+now.strftime('%Y-%m-%d %H:%M UTC'),11,'#8b949e')
    svg.append('</svg>')
    return '\n'.join(svg)+'\n'

def main():
    if os.environ.get('PROFILE_PREVIEW'):
        stats=json.loads((ROOT/'preview-stats.json').read_text())
    else:
        stats=collect()
    (ROOT/'profile.svg').write_text(render(stats))
    print('Rendered profile.svg')

if __name__ == '__main__':
    main()
