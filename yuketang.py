import asyncio
import websockets
import json
import requests
import os
import time
import traceback
from util import *
from send import *
from random import *

current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

yt_config = config['yuketang']
timeout = yt_config['timeout']
domain = yt_config['domain']

class yuketang:
    
    shared_answers = {}
    
    def __init__(self, name, openId) -> None:
        self.name = name
        self.openId = openId
        self.cookie=''
        self.cookie_time=''
        self.lessonIdNewList=[]
        self.lessonIdDict = {}
        self.classroomCodeList = yt_config['classroomCodeList']
        self.classroomWhiteList = yt_config['classroomWhiteList']
        self.clashroomBlackList = yt_config['clashroomBlackList']
        self.clashroomStartTimeDict = yt_config['clashroomStartTimeDict']
        self.wx = yt_config['wx']
        self.dd = yt_config['dd']
        self.fs = yt_config['fs']
        self.an = yt_config['an']
        self.ppt = yt_config['ppt']
        self.si = yt_config['si']
        self.msgmgr=SendManager(openId=self.openId,wx=self.wx,dd=self.dd,fs=self.fs)

    async def getcookie(self):
        flag = 0
        def read_cookie():
            with open(f"{self.name}cookie", "r") as f:
                lines = f.readlines()
            self.cookie = lines[0].strip()
            if len(lines) >= 2:
                self.cookie_time = convert_date(int(lines[1].strip()))
            else:
                self.cookie_time = ''
        while True:
            if not os.path.exists(f"{self.name}cookie"):
                flag = 1
                self.msgmgr.sendMsg("正在第一次获取登录cookie, 请微信扫码")
                await self.ws_controller(self.ws_login, retries=1000, delay=1)
            if not self.cookie:
                flag = 1
                read_cookie()
            if self.cookie_time and not check_time(self.cookie_time, 0):
                flag = 1
                self.msgmgr.sendMsg(f"cookie已失效, 请重新扫码")
                await self.ws_controller(self.ws_login, retries=1000, delay=1)
                read_cookie()
                continue
            elif self.cookie_time and (not check_time(self.cookie_time, 2880) and datetime.now().minute < 5 or not check_time(self.cookie_time, 120)):
                flag = 1
                self.msgmgr.sendMsg(f"cookie有效至{self.cookie_time}, 即将失效, 请重新扫码")
                await self.ws_controller(self.ws_login, retries=0, delay=1)
                read_cookie()
                continue
            code = self.check_cookie()
            if code == 1:
                flag = 1
                self.msgmgr.sendMsg(f"cookie已失效, 请重新扫码")
                await self.ws_controller(self.ws_login, retries=1000, delay=1)
                read_cookie()
            elif code == 2:
                self.msgmgr.sendMsg(f"检测cookie有效性失败")
            else:
                if self.cookie_time and flag == 1 and check_time(self.cookie_time, 2880):
                    self.msgmgr.sendMsg(f"cookie有效至{self.cookie_time}")
                elif self.cookie_time and flag == 1:
                    self.msgmgr.sendMsg(f"cookie有效至{self.cookie_time}, 即将失效, 下个小时初注意扫码")
                elif flag == 1:
                    self.msgmgr.sendMsg(f"cookie有效, 有效期未知")
                break

    def weblogin(self,UserID,Auth):
        url=f"https://{domain}/pc/web_login"
        data={
            "UserID":UserID,
            "Auth":Auth
        }
        headers={
            "referer":f"https://{domain}/web?next=/v2/web/index&type=3",
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Content-Type":"application/json"
        }
        try:
            res=requests.post(url=url,headers=headers,json=data,timeout=timeout)
        except Exception as e:
            print(f"登录失败: {e}")
            return
        cookies = res.cookies
        self.cookie=""
        for k,v in cookies.items():
            self.cookie += f'{k}={v};'
        date = cookie_date(res)
        if date:
            content = f'{self.cookie}\n{date}'
            self.cookie_time = convert_date(int(date))
        else:
            content = self.cookie
        with open(f"{self.name}cookie","w")as f:
            f.write(content)

    def check_cookie(self):
        info=self.get_basicinfo()
        if not info:
            return 2
        if info.get("code")==0:
            return 0
        return 1
    
    def setAuthorization(self,res,lessonId):
        if res.headers.get("Set-Auth") is not None:
            self.lessonIdDict[lessonId]['Authorization']="Bearer "+res.headers.get("Set-Auth")

    def join_classroom(self):
        url=f"https://{domain}/v/course_meta/join_classroom"
        headers={
            "cookie":self.cookie,
            "x-csrftoken":self.cookie.split("csrftoken=")[1].split(";")[0],
            "Content-Type":"application/json"
        }
        classroomCodeList_del = []
        for classroomCode in self.classroomCodeList:
            data={"id":classroomCode}
            try:
                res=requests.post(url=url,headers=headers,json=data,timeout=timeout)
            except Exception as e:
                return
            if res.json().get("success", False) == True:
                self.msgmgr.sendMsg(f"班级邀请码/课堂暗号{classroomCode}使用成功")
                classroomCodeList_del.append(classroomCode)
            elif "班级邀请码或课堂暗号不存在" in res.json().get("msg", ""):
                self.msgmgr.sendMsg(f"班级邀请码/课堂暗号{classroomCode}不存在")
                classroomCodeList_del.append(classroomCode)
            # else:
            #    self.msgmgr.sendMsg(f"班级邀请码/课堂暗号{classroomCode}使用失败")
        self.classroomCodeList = list(set(self.classroomCodeList) - set(classroomCodeList_del))

    def get_basicinfo(self):
        url=f"https://{domain}/api/v3/user/basic-info"
        headers={
            "referer":f"https://{domain}/web?next=/v2/web/index&type=3",
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "cookie":self.cookie
        }
        try:
            res=requests.get(url=url,headers=headers,timeout=timeout).json()
            return res
        except Exception as e:
            return {}

    def lesson_info(self,lessonId):
        url=f"https://{domain}/api/v3/lesson/basic-info"
        headers={
            "referer":f"https://{domain}/lesson/fullscreen/v3/{lessonId}?source=5",
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "cookie":self.cookie,
            "Authorization":self.lessonIdDict[lessonId]['Authorization']
        }
        try:
            res=requests.get(url=url,headers=headers,timeout=timeout)
        except Exception as e:
            return
        self.setAuthorization(res,lessonId)
        classroomName = self.lessonIdDict[lessonId]['classroomName']
        try:
            self.lessonIdDict[lessonId]['title'] = res.json()['data']['title']
            self.lessonIdDict[lessonId]['header'] = f"课程: {classroomName}\n标题: {self.lessonIdDict[lessonId]['title']}\n教师: {res.json()['data']['teacher']['name']}\n开始时间: {convert_date(res.json()['data']['startTime'])}"
        except Exception as e:
            self.lessonIdDict[lessonId]['title'] = '未知标题'
            self.lessonIdDict[lessonId]['header'] = f"课程: {classroomName}\n标题: 获取失败\n教师: 获取失败\n开始时间: 获取失败"

    def getlesson(self):
        url=f"https://{domain}/api/v3/classroom/on-lesson-upcoming-exam"
        headers={
            "referer":f"https://{domain}/web?next=/v2/web/index&type=3",
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "cookie":self.cookie
        }
        try:
            online_data=requests.get(url=url,headers=headers,timeout=timeout).json()
        except Exception as e:
            return False
        try:
            self.lessonIdNewList = []
            if online_data['data']['onLessonClassrooms'] == []:
                for lessonId in self.lessonIdDict:
                    self.lessonIdDict[lessonId].get('websocket', '').close()
                self.lessonIdDict = {}
                return False
            for item in online_data['data']['onLessonClassrooms']:
                if (self.classroomWhiteList and item['courseName'] not in self.classroomWhiteList) or item['courseName'] in self.clashroomBlackList or (self.clashroomStartTimeDict and item['courseName'] in self.clashroomStartTimeDict and not check_time2(self.clashroomStartTimeDict[item['courseName']])):
                    continue
                lessonId = item['lessonId']
                if lessonId not in self.lessonIdDict:
                    self.lessonIdNewList.append(lessonId)
                    self.lessonIdDict[lessonId] = {}
                    self.lessonIdDict[lessonId]['start_time'] = time.time()
                    self.lessonIdDict[lessonId]['classroomName'] = item['courseName']
                self.lessonIdDict[lessonId]['active'] = '1'
            to_delete = [lessonId for lessonId, details in self.lessonIdDict.items() if not details.get('active', '0') == '1']
            for lessonId in to_delete:
                del self.lessonIdDict[lessonId]
                self.lessonIdDict[lessonId].get('websocket', '').close()
            for lessonId in self.lessonIdDict:
                self.lessonIdDict[lessonId]['active'] = '0'
            if self.lessonIdNewList:
                return True
            else:
                return False
        except Exception as e:
            return False

    def lesson_checkin(self):
        for lessonId in self.lessonIdNewList:
            url=f"https://{domain}/api/v3/lesson/checkin"
            headers={
                "referer":f"https://{domain}/lesson/fullscreen/v3/{lessonId}?source=5",
                "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
                "Content-Type":"application/json; charset=utf-8",
                "cookie":self.cookie
            }
            data={
                "source":5,
                "lessonId":lessonId
            }
            try:
                res=requests.post(url=url,headers=headers,json=data,timeout=timeout)
            except Exception as e:
                return
            self.setAuthorization(res,lessonId)
            self.lesson_info(lessonId)
            try:
                self.lessonIdDict[lessonId]['Auth'] = res.json()['data']['lessonToken']
                self.lessonIdDict[lessonId]['userid'] = res.json()['data']['identityId']
            except Exception as e:
                self.lessonIdDict[lessonId]['Auth'] = ''
                self.lessonIdDict[lessonId]['userid'] = ''
            checkin_status = res.json()['msg']
            if checkin_status == 'OK':
                self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 签到成功")
            elif checkin_status == 'LESSON_END':
                self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 课程已结束")
            else:
                self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 签到失败")
    
    def fetch_problems(self, lessonId):
        url = f"https://{domain}/api/v3/lesson/presentation/fetch?presentation_id={self.lessonIdDict[lessonId]['presentation']}"
        headers = {
            "referer": f"https://{domain}/lesson/fullscreen/v3/{lessonId}?source=5",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "cookie": self.cookie,
            "Authorization": self.lessonIdDict[lessonId]['Authorization']
        }
        res=requests.get(url, headers=headers, timeout=timeout)
        self.setAuthorization(res, lessonId)
        info = res.json()
        slides=info['data']['slides']    #获得幻灯片列表
        for slide in slides:
            if slide['id'] == self.lessonIdDict[lessonId]['problemId']:
                if slide.get("problem") is not None:  
                    self.lessonIdDict[lessonId]['problems'][slide['id']]=slide['problem']
                    self.lessonIdDict[lessonId]['problems'][slide['id']]['index']=slide['index'] 
                    if slide['problem']['body'] == '':
                        shapes = slide.get('shapes', [])
                        if shapes:
                            min_left_item = min(shapes, key=lambda item: item.get('Left', 9999999))
                            if min_left_item != 9999999 and min_left_item.get('Text') is not None:
                                self.lessonIdDict[lessonId]['problems'][slide['id']]['body'] = min_left_item['Text']
                            else:
                                self.lessonIdDict[lessonId]['problems'][slide['id']]['body'] = '未知问题'
                        else:
                            self.lessonIdDict[lessonId]['problems'][slide['id']]['body'] = '未知问题'
                            
                    shared_answer = yuketang.shared_answers.get(slide['id'])     
                    if shared_answer is not None:
                        self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'] = shared_answer
                        self.msgmgr.sendMsg(f"问题: {self.lessonIdDict[lessonId]['problems'][slide['id']]['body']}\n检测到共享答案: {shared_answer}")
                        # 跳过后续逻辑，直接使用共享答案
                        break   
    
                    if self.lessonIdDict[lessonId]['problems'][slide['id']]['problemType'] == 5:
                        if self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'] in [[],None,'null'] and not self.lessonIdDict[lessonId]['problems'][slide['id']]['result'] in [[],None,'null']:
                            yuketang.shared_answers[slide['id']] = self.lessonIdDict[lessonId]['problems'][slide['id']]['result']
                            self.msgmgr.sendMsg(f"问题: {self.lessonIdDict[lessonId]['problems'][slide['id']]['body']}\n答案:{yuketang.shared_answers[slide['id']]}已提交到共享区")
                            self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'] = yuketang.shared_answers[slide['id']]
                            break
                    elif self.lessonIdDict[lessonId]['problems'][slide['id']]['problemType'] == 4:
                        num_blanks = len(self.lessonIdDict[lessonId]['problems'][slide['id']]['blanks'])
                        if not check_answers_in_blanks(self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'], num_blanks):
                            if check_answers_in_blanks(self.lessonIdDict[lessonId]['problems'][slide['id']]['result'], num_blanks):
                                yuketang.shared_answers[slide['id']] = self.lessonIdDict[lessonId]['problems'][slide['id']]['result']   
                                self.msgmgr.sendMsg(f"问题: {self.lessonIdDict[lessonId]['problems'][slide['id']]['body']}\n答案:{yuketang.shared_answers[slide['id']]}已提交到共享区")  
                                self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'] = yuketang.shared_answers[slide['id']]      
                                break
                    else:
                        if not check_answers_in_options(self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'], self.lessonIdDict[lessonId]['problems'][slide['id']]['options']) and check_answers_in_options(self.lessonIdDict[lessonId]['problems'][slide['id']]['result'], self.lessonIdDict[lessonId]['problems'][slide['id']]['options']):
                            yuketang.shared_answers[slide['id']] = self.lessonIdDict[lessonId]['problems'][slide['id']]['result']
                            self.msgmgr.sendMsg(f"问题: {self.lessonIdDict[lessonId]['problems'][slide['id']]['body']}\n答案:{yuketang.shared_answers[slide['id']]}已提交到共享区")
                            self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'] = yuketang.shared_answers[slide['id']]
                            break
 

    def fetch_presentation(self, lessonId):
        url = f"https://{domain}/api/v3/lesson/presentation/fetch?presentation_id={self.lessonIdDict[lessonId]['presentation']}"
        headers = {
            "referer": f"https://{domain}/lesson/fullscreen/v3/{lessonId}?source=5",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "cookie": self.cookie,
            "Authorization": self.lessonIdDict[lessonId]['Authorization']
        }
        res=requests.get(url, headers=headers, timeout=timeout)
        self.setAuthorization(res, lessonId)
        info = res.json()
        slides=info['data']['slides']    #获得幻灯片列表
        self.lessonIdDict[lessonId]['problems']={}
        self.lessonIdDict[lessonId]['covers']=[slide['index'] for slide in slides if slide.get('cover') is not None]
        for slide in slides:
            if slide.get("problem") is not None:
                self.lessonIdDict[lessonId]['problems'][slide['id']]=slide['problem']
                self.lessonIdDict[lessonId]['problems'][slide['id']]['index']=slide['index']
                if slide['problem']['body'] == '':
                    shapes = slide.get('shapes', [])
                    if shapes:
                        min_left_item = min(shapes, key=lambda item: item.get('Left', 9999999))
                        if min_left_item != 9999999 and min_left_item.get('Text') is not None:
                            self.lessonIdDict[lessonId]['problems'][slide['id']]['body'] = min_left_item['Text']
                        else:
                            self.lessonIdDict[lessonId]['problems'][slide['id']]['body'] = '未知问题'
                    else:
                        self.lessonIdDict[lessonId]['problems'][slide['id']]['body'] = '未知问题'
                        
                if self.lessonIdDict[lessonId]['problems'][slide['id']]['problemType'] == 5:
                    if self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'] in [[],None,'null'] and not self.lessonIdDict[lessonId]['problems'][slide['id']]['result'] in [[],None,'null']:
                        yuketang.shared_answers[slide['id']] = self.lessonIdDict[lessonId]['problems'][slide['id']]['result']
                elif self.lessonIdDict[lessonId]['problems'][slide['id']]['problemType'] == 4:
                    num_blanks = len(self.lessonIdDict[lessonId]['problems'][slide['id']]['blanks'])
                    if not check_answers_in_blanks(self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'], num_blanks):
                        if check_answers_in_blanks(self.lessonIdDict[lessonId]['problems'][slide['id']]['result'], num_blanks):
                            yuketang.shared_answers[slide['id']] = self.lessonIdDict[lessonId]['problems'][slide['id']]['result']         
                else:
                    if not check_answers_in_options(self.lessonIdDict[lessonId]['problems'][slide['id']]['answers'], self.lessonIdDict[lessonId]['problems'][slide['id']]['options']) and check_answers_in_options(self.lessonIdDict[lessonId]['problems'][slide['id']]['result'], self.lessonIdDict[lessonId]['problems'][slide['id']]['options']) and not self.lessonIdDict[lessonId]['problems'][slide['id']]['result'] in [[],None,'null']:
                        yuketang.shared_answers[slide['id']] = self.lessonIdDict[lessonId]['problems'][slide['id']]['result']
        if self.lessonIdDict[lessonId]['problems']=={}:
            self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n问题列表: 无")
        else:
            self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n{format_json_to_text(self.lessonIdDict[lessonId]['problems'], self.lessonIdDict[lessonId].get('unlockedproblem', []))}")
        folder_path=lessonId

        
        async def fetch_presentation_background():
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, clear_folder, folder_path)
            await loop.run_in_executor(None, download_images_to_folder, slides, folder_path)
            output_pdf_path=os.path.join(folder_path, f"{self.lessonIdDict[lessonId]['classroomName']}-{self.lessonIdDict[lessonId]['title']}.pdf")
            await loop.run_in_executor(None, images_to_pdf, folder_path, output_pdf_path)
            if os.path.exists(output_pdf_path):
                try:
                    self.msgmgr.sendFile(output_pdf_path)
                except Exception as e:
                    self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: PPT推送失败")
            else:
                self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 没有PPT")
        if self.ppt:
            asyncio.create_task(fetch_presentation_background())

    async def answer(self,lessonId):
        url=f"https://{domain}/api/v3/lesson/problem/answer"
        headers={
            "referer":f"https://{domain}/lesson/fullscreen/v3/{lessonId}?source=5",
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "cookie":self.cookie,
            "Content-Type":"application/json",
            "Authorization":self.lessonIdDict[lessonId]['Authorization']
        }

        data={
            "dt":int(time.time()*1000),
            "problemId":self.lessonIdDict[lessonId]['problemId'],
            "problemType":self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]['problemType'],
            "result":self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]['answers']
        }
        try:
            res=requests.post(url=url,headers=headers,json=data,timeout=timeout)
        except Exception as e:
            return
        self.setAuthorization(res,lessonId)
        self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\nPPT: 第{self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]['index']}页\n问题: {self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]['body']}\n提交答案: {self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]['answers']}")

    async def ws_controller(self, func, *args, retries=3, delay=10):
        attempt = 0
        while attempt <= retries:
            try:
                await func(*args)
                return  # 如果成功就直接返回
            except Exception as e:
                print(traceback.format_exc())
                attempt += 1
                if attempt <= retries:
                    await asyncio.sleep(delay)
                    print(f"出现异常, 尝试重试 ({attempt}/{retries})")
            except asyncio.CancelledError:
                print("操作已超时,等待下次尝试")

    async def ws_login(self):
        uri = f"wss://{domain}/wsapp/"
        async with websockets.connect(uri, ping_timeout=180, ping_interval=5) as websocket:
            # 发送 "hello" 消息以建立连接
            hello_message = {
                "op":"requestlogin",
                "role":"web",
                "version":1.4,
                "type":"qrcode",
                "from":"web"
            }
            await websocket.send(json.dumps(hello_message))
            server_response = await recv_json(websocket)
            qrcode_url=server_response['ticket']
            download_qrcode(qrcode_url, self.name)
            self.msgmgr.sendImage(f"{self.name}qrcode.jpg")
            server_response = await asyncio.wait_for(recv_json(websocket),timeout=60)
            self.weblogin(server_response['UserID'],server_response['Auth'])
            
    async def countdown(self, limit):
            try:
                # 等待 limit 秒，或者事件被触发以取消倒计时
                await asyncio.wait_for(self.stop_event.wait(), timeout=limit)
            except asyncio.TimeoutError:
                # 超时表示 limit 时间到了，倒计时正常结束
                self.stop_event.set()
                self.msgmgr.sendMsg(f"问题正常结束")
            else:
                # 如果事件触发，表示提前结束
                self.msgmgr.sendMsg(f"问题已提前结束")
        
    async def listen_for_problemfinished(self, lessonId, limit):
    # 监听 problemfinished 的消息
        while not self.stop_event.is_set():
            try:
                server_response = await asyncio.wait_for(recv_json(self.lessonIdDict[lessonId]['websocket']), timeout=limit)
                if server_response['op'] == "problemfinished":
                    self.stop_event.set()
                    break
            except asyncio.TimeoutError:
                break
            except Exception as e:
                self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 连接断开")
                break
            
    async def receive_messages(self,lessonId):
        await self.pull_probleminfo(lessonId)
        while not self.stop_event.is_set():
            try:
                server_response = await recv_json(self.lessonIdDict[lessonId]['websocket'])
            except Exception as e:
                self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 连接断开")
                break
            op=server_response['op']
            if op == "probleminfo" :
                limit = server_response.get('limit')  # 检查是否有 limit 值
                if limit is not None and limit > 0:
                    self.msgmgr.sendMsg(f"问题开始，倒计时 {limit} 秒")
                    await asyncio.gather(
                        self.countdown(limit),  # 倒计时任务
                        self.listen_for_problemfinished(lessonId,limit)  # 监听 "problemfinished" 任务
                    )
                    break
                else:
                    self.msgmgr.sendMsg(f"问题无倒计时")
            if op=="problemfinished":
                self.stop_event.set()
                self.msgmgr.sendMsg(f"问题已结束")
                break
            
    async def fetch_answers(self, lessonId):
         while not self.stop_event.is_set():
         # 获取幻灯片信息，处理可能的异常
            self.fetch_problems(lessonId)
            await asyncio.sleep(2)

            # 检查当前问题的答案是否存在，如果存在则提交
            if self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']].get('answers'):
                await self.answer(lessonId)
                self.stop_event.set()
                break  # 提交答案后退出循环
            
    async def pull_probleminfo(self, lessonId):
        # 构造要发送的消息
        probleminfo_message = {
            "op": "probleminfo",
            "lessonid": lessonId,
            "problemid": self.lessonIdDict[lessonId]['problemId'],
            "msgid": self.lessonIdDict[lessonId]['msgid']
        }
        
        # 发送消息到 WebSocket
        await self.lessonIdDict[lessonId]['websocket'].send(json.dumps(probleminfo_message))
        # 递增 msgid，确保每条消息的唯一性
        self.lessonIdDict[lessonId]['msgid'] += 1
        
                 

    async def ws_lesson(self,lessonId):
        flag_ppt=1
        flag_si=1
        self.lessonIdDict[lessonId]['msgid'] = 1
        def del_dict():
            nonlocal flag_ppt, flag_si
            flag_ppt=1
            flag_si=1
            keys_to_remove = ['presentation', 'si', 'unlockedproblem', 'covers']
            for key in keys_to_remove:
                if self.lessonIdDict[lessonId].get(key) is not None:
                    del self.lessonIdDict[lessonId][key]
        del_dict()
        uri = f"wss://{domain}/wsapp/"
        async with websockets.connect(uri, ping_timeout=180, ping_interval=15) as websocket:
            # 发送 "hello" 消息以建立连接
            hello_message = {
                "op": "hello",
                "userid": self.lessonIdDict[lessonId]['userid'],
                "role": "student",
                "auth": self.lessonIdDict[lessonId]['Auth'],
                "lessonid": lessonId
            }
            await websocket.send(json.dumps(hello_message))
            self.lessonIdDict[lessonId]['websocket'] = websocket
            while True and time.time()-self.lessonIdDict[lessonId]['start_time']<36000:
                try:
                    server_response = await recv_json(websocket)
                except Exception as e:
                    self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 连接断开")
                    break
                op=server_response['op']
                if op=="hello" or op=="fetchtimeline":
                    reversed_timeline = list(reversed(server_response['timeline']))
                    for item in reversed_timeline:
                        if 'pres' in item:
                            if flag_ppt==0 and self.lessonIdDict[lessonId]['presentation'] != item['pres']:
                                del_dict()
                                self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 课件更新")
                            self.lessonIdDict[lessonId]['presentation']=item['pres']
                            self.lessonIdDict[lessonId]['si']=item['si']
                            break
                    if server_response.get('presentation'):
                        if flag_ppt==0 and self.lessonIdDict[lessonId]['presentation'] != server_response['presentation']:
                            del_dict()
                            self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 课件更新")
                        self.lessonIdDict[lessonId]['presentation']=server_response['presentation']
                    if server_response.get('slideindex'):
                        self.lessonIdDict[lessonId]['si']=server_response['slideindex']
                    if server_response.get('unlockedproblem'):
                        self.lessonIdDict[lessonId]['unlockedproblem']=server_response['unlockedproblem']
                elif op=="showpresentation" or op=="presentationupdated" or op=="presentationcreated":
                    if server_response.get('presentation'):
                        if flag_ppt==0 and self.lessonIdDict[lessonId]['presentation'] != server_response['presentation']:
                            del_dict()
                            self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 课件更新")
                        self.lessonIdDict[lessonId]['presentation']=server_response['presentation']
                    if server_response.get('slideindex'):
                        self.lessonIdDict[lessonId]['si']=server_response['slideindex']
                    if server_response.get('unlockedproblem'):
                        self.lessonIdDict[lessonId]['unlockedproblem']=server_response['unlockedproblem']
                elif op=="slidenav":
                    if server_response['slide'].get('pres'):
                        if flag_ppt==0 and self.lessonIdDict[lessonId]['presentation'] != server_response['slide']['pres']:
                            del_dict()
                            self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 课件更新")
                        self.lessonIdDict[lessonId]['presentation']=server_response['slide']['pres']
                    if server_response['slide'].get('si'):
                        self.lessonIdDict[lessonId]['si']=server_response['slide']['si']
                    if server_response.get('unlockedproblem'):
                        self.lessonIdDict[lessonId]['unlockedproblem']=server_response['unlockedproblem']
                elif op=="unlockproblem":
                    if server_response['problem'].get('pres'):
                        if flag_ppt==0 and self.lessonIdDict[lessonId]['presentation'] != server_response['problem']['pres']:
                            del_dict()
                            self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 课件更新")
                        self.lessonIdDict[lessonId]['presentation']=server_response['problem']['pres']
                    if server_response['problem'].get('si'):
                        self.lessonIdDict[lessonId]['si']=server_response['problem']['si']
                    if server_response.get('unlockedproblem'):
                        self.lessonIdDict[lessonId]['unlockedproblem']=server_response['unlockedproblem']
                    self.lessonIdDict[lessonId]['problemId']=server_response['problem']['prob']
                    text_result = f"PPT: 第{self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]['index']}页\n问题: {self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']].get('body', '未知问题')}\n"
                    answers = self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']].get('answers', [])
                    if 'options' in self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]:
                        for option in self.lessonIdDict[lessonId]['problems'][self.lessonIdDict[lessonId]['problemId']]['options']:
                            text_result += f"- {option['key']}: {option['value']}\n"
                    if answers not in [[],None,'null']:
                        answer_text = ', '.join(answers)
                        text_result += f"答案: {answer_text}\n"
                    else:
                        text_result += "答案: 暂无\n"
                    self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n解锁问题:\n{text_result}")
                    if self.an:
                        self.stop_event = asyncio.Event()
                        if flag_ppt==1 and self.lessonIdDict[lessonId].get('presentation') is not None:
                            flag_ppt=0
                            self.fetch_presentation(lessonId)
                        
                        try:
                            await asyncio.wait_for(
                                asyncio.gather(
                                    self.receive_messages(lessonId),
                                    self.fetch_answers(lessonId)
                                ),
                                timeout=420  # 设置超时时间为 7 分钟
                            )
                        except asyncio.TimeoutError:
                            # 处理超时的情况，例如记录日志或者通知用户
                            self.msgmgr.sendMsg(f"问题超时已取消")
                        self.stop_event.clear()
                        
                elif op=="lessonfinished":
                    self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 下课了")
                    break
                if flag_ppt==1 and self.lessonIdDict[lessonId].get('presentation') is not None:
                    flag_ppt=0
                    self.fetch_presentation(lessonId)
                if flag_si==1 and self.lessonIdDict[lessonId].get('si') is not None and self.lessonIdDict[lessonId].get('covers') is not None and self.lessonIdDict[lessonId]['si'] in self.lessonIdDict[lessonId]['covers']:
                    self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 正在播放PPT第{self.lessonIdDict[lessonId]['si']}页")
                    if self.si:
                        del self.lessonIdDict[lessonId]['si']
                    else:
                        flag_si=0
            self.msgmgr.sendMsg(f"{self.lessonIdDict[lessonId]['header']}\n消息: 连接关闭")
            del self.lessonIdDict[lessonId]
            yuketang.shared_answers = {}
            

    async def lesson_attend(self):
        tasks = [asyncio.create_task(self.ws_lesson(lessonId)) for lessonId in self.lessonIdNewList]
        asyncio.gather(*tasks)
        self.lessonIdNewList = []

async def ykt_user(ykt):
    while True:
        await ykt.getcookie()
        ykt.join_classroom()
        if ykt.getlesson():
            ykt.lesson_checkin()
            await ykt.lesson_attend()
        asyncio.sleep(30)
