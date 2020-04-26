import os
import http.server
import json
import threading
import multiprocessing.pool
import subprocess

events = ["Push Hook",
          "Tag Push Hook",
          "Issue Hook",
          "Note Hook",
          "Merge Request Hook",
          "Wiki Page Hook",
          "Pipeline Hook",
          "Job Hook"]

def handle_hook(event, token, obj, config):
    try:
        handle_hook_c(event, token, obj, config)
    except Exception as e:
        print(e)

def handle_hook_c(event, token, obj, config):
    if 'project' not in obj or type(obj['project']) != dict:
        return
    if 'web_url' not in obj['project'] or type(obj['project']['web_url']) != str:
        return
    weburl = obj['project']['web_url']
    if 'ref' not in obj or type(obj['ref']) != str:
        return
    ref = obj['ref']
    print("Hook: ", event, weburl, ref)
    # find repositories
    found_repos = []
    for repo in config.repositories:
        if repo.gitlaburl == weburl and repo.gitlabtoken == token and (repo.ref == None or repo.ref == ref) and (repo.hooks == None or len(repo.hooks) == 0 or event in repo.hooks):
            print(" *  ", repo.name, repo.gitlaburl, repo.ref, repo.hooks)
            found_repos.append(repo)
    if len(found_repos) == 0:
        return
    # find programs
    found_cmds = []
    for cmd in config.commands:
        for repo in found_repos:
            if cmd.repo == repo.name:
                print(" -> ", cmd.name)
                found_cmds.append(cmd)
                break
    if len(found_cmds) == 0:
        return
    # execute programs
    env = {}
    env['GITLAB_URL'] = weburl
    env['GITLAB_TOKEN'] = token
    env['GITLAB_REF'] = ref
    env['GITLAB_EVENT'] = event
    for cmd in found_cmds:
        res = cmd.exec(env)
        if cmd.ignore_error == False and res != 0:
            break


class GitlabHookHandler(http.server.BaseHTTPRequestHandler):

    def send_error(self, code, message=None, explain=None):
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header('Connection', 'close')
        self.end_headers()

    def do_POST(self):
        event = None
        token = None
        if "X-Gitlab-Event" in self.headers:
            event = self.headers["X-Gitlab-Event"]
        if "X-Gitlab-Token" in self.headers:
            token = self.headers["X-Gitlab-Token"]
        if event == None or token == None:
            self.send_error(http.HTTPStatus.FORBIDDEN, "Forbidden")
            return

        if 'Content-Length' not in self.headers:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "Bad request")
            return

        # get body
        length = None
        try:
            length = int(self.headers['Content-Length'])
        except:
            pass
        if length == None:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "Bad request")
            return
        text = None
        try:
            text = self.rfile.read(length)
        except:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "Bad request")
            return 
        json_obj = None
        try:
            json_obj = json.loads(text)
        except Exception as e:
            pass
        if json_obj == None:
            self.send_error(http.HTTPStatus.BAD_REQUEST, "Bad request")
            return

        self.handle_request(event, token, json_obj)

        self.log_request(http.HTTPStatus.OK)
        self.send_response_only(http.HTTPStatus.OK)
        self.send_header('Connection', 'close')
        self.end_headers()
        
    def handle_request(self, event, token, json_obj):
        pass

class GitlabHookServer(threading.Thread):
    def __init__(self, interface, port, configjson, workers=2):
        config = GitlabHookConfig.fromConfig(configjson)
        self.config = config
        self.configjson = configjson
        pool = multiprocessing.pool.ThreadPool()
        self.pool = pool
        class PrivateGitlabHookHandler(GitlabHookHandler):
            def handle_request(self, event, token, json_obj):
                pool.apply_async(handle_hook, (event, token, json_obj, config))
        print("Start server on ", interface, port)
        self.httpd = http.server.HTTPServer((interface, port), PrivateGitlabHookHandler)
        threading.Thread.__init__(self)
    def run(self):
        self.httpd.serve_forever()
    def stopServer(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.pool.close()
        self.pool.join()
        self.pool.terminate()

class Command:
    def __init__(self, name, prog, reponame):
        # config
        self.name = name
        self.prog = prog
        self.repo = reponame
        self.workingdir = None
        self.ignore_error = False
        self.hooks = None
    def fromConfig(config):
        j = Command(config["name"], config["exec"], config["repo"])
        if "workingdir" in config:
            j.workingdir = config["workingdir"]
        if "ignore_error" in config:
            j.ignore_error = config["ignore_error"]
        if 'hook' in config and type(config['hook']) == list:
            hooks = config['hook']
            for h in hooks:
                if type(h) != str:
                    print("Wrong config value: ", config["name"], "hooks")
                if h not in events:
                    print("Unknown hook event: ", h)
            j.hooks = hooks
        return j
    def exec(self, env):
        cmd = self.prog
        print("Prog", self.name, "execute", " ".join(cmd))
        # create new environment
        new_env = os.environ.copy()
        new_env.update(env)
        # run process
        process = subprocess.Popen(cmd, env=new_env, cwd=self.workingdir)
        process.wait()
        print("Prog", self.name, "Return:", process.returncode)
        return process.returncode

class Repository:
    def __init__(self, name, url, token):
        self.name = name
        self.gitlaburl = url
        self.gitlabtoken = token
        self.ref = None
        self.hooks = None
    def fromConfig(config):
        r = Repository(config["name"], config["gitlaburl"], config["gitlabtoken"])
        if 'ref' in config:
            r.ref = config['ref']
        if 'hook' in config and type(config['hook']) == list:
            hooks = config['hook']
            for h in hooks:
                if type(h) != str:
                    print("Wrong config value: ", config["name"], "hooks")
                if h not in events:
                    print("Unknown hook event: ", h)
            r.hooks = hooks
        return r

class GitlabHookConfig:
    def __init__(self):
        self.interface = ""
        self.port = None
        self.repositories = []
        self.commands = []
    def fromConfig(config):
        c = GitlabHookConfig()
        if 'interface' in config:
            c.interface = config['interface']
        if 'port' in config:
            c.port = config['port']
        for r in config['repositories']:
            r = Repository.fromConfig(r)
            c.repositories.append(r)
        for e in config['commands']:
            cmd = Command.fromConfig(e)
            c.commands.append(cmd)
        return c
