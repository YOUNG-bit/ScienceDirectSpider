'''
    基本思路
    1、首先进入网站，用户输入要查找的年份和哪一期
    2、然后找到scipt，找到volume x y，并判断有没有
    3、只要给定了volumn x y就可以进入这个期刊
    4、
'''
import requests
from bs4 import BeautifulSoup
import re
import json
import xlwt
from tqdm import tqdm
import pandas as pd
import  time
import threading
import queue

class myThread(threading.Thread):
    def __init__(self, name, url_q, sc, bar):
        threading.Thread.__init__(self)
        self.name = name
        self.q = url_q
        self.sc = sc # 这个是传过来的ScienceDirect类
        self.pbar = bar
        print('进程' + name + '创建成功')

    def run(self):
        # print("Starting " + self.name)
        while True:
            try:
                id = self.q.get(timeout=2)
                self.pbar.update(1)
                sc.get_articles_info(id[0],id[1],id[2])
            except:
                break
        print("Exiting" + self.name)


class myThread2(threading.Thread):
    def __init__(self,name,q,sc,bar):
        threading.Thread.__init__(self)
        self.name = name
        self.q = q
        self.sc = sc
        self.pbar = bar
        print('进程' +name + '创建成功')
    def run(self):
        # print('Starting' + self.name)
        while True:
            try:
                id = self.q.get(timeout=2)
                self.pbar.update(1)
                self.sc.get_all_articls_url(id[0],id[1])
            except:
                break
        print('Exiting' + self.name)


class ScienceDirect:

    def __init__(self, title='journal-of-informetrics'):
        self.result_dic = {}
        self.soup1 = []
        self.volumn_list = []
        self.title = title
        self.count_articles = 0  # 记录文章个数
        self.count_issues = 0  # 记录所有的期刊个数
        self.time_raw = r'(January|February|March|April|May|June|July|August|September|October|November|December) ([0-9]{4})'

    def write_to_json(self):
        with open('result_dic.json', 'w') as f:
            json.dump(self.result_dic, f)

    def inter_journal(self):
        # 获取当前journal下的全部issues
        # url = 'https://www.sciencedirect.com/journal/' + self.title + '/issues'
        url = input('请输入想要查看期刊下面的全部issues的网址:')
        page = int(input('请输入期刊issue页数:'))
        # 为了安全访问，修改header
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/80.0.3987.162 Safari/537.36'}
        # 获取网站
        for i in range(1,page+1):
            try:
                url2 = url + '?page=' + str(i)
                Re = requests.get(url2, headers=headers)
                print(Re)
                self.soup1.append(BeautifulSoup(Re.text, 'html.parser'))
            except:
                print('访问journal产生异常')

    # print('ok')

    '''
        input:
            获取从期刊volumn x到volumn y的全部期刊网站数据
            soup代表网站的树结构
        ideas:
            首先需要判断是否存在Volumn x, Issue num,
            然后根据Volumn x, Issue num获取此期刊的网址
            根据其网址找到获取全部的期刊网站（可能需要翻页功能）
        output:
            最后作为一个词典返回，记录分别存在哪个期刊下面
    '''

    def get_volume(self):
        # 这里默认查找全部期刊信息所在的那个脚本
        volumes = []
        only_volume = []
        for soup in self.soup1:
            all_str = soup.find_all(type = 'application/json')[0]
            if all_str == []:
                print('在源代码中找不到期刊信息')
                return
            # 转换成为字符串
            s = ''.join(all_str)
            # 获取全部期刊信息
            # 信息中存在有Issue的，还有没有issue的，但是还有二者都有的，所以这里需要都添加进来
            ls = re.findall(r'Volume [0-9]+, Issue [0-9]+', s)
            ls_special = re.findall(r'Volume [0-9]+, Part [0-9]+', s)
            for i in ls_special:
                ls.append(i)
            # 先将有issue的加到列表里
            ls = set(ls)
            ls = list(ls)
            for l in ls:
                self.volumn_list.append(l)
                vs = l.split(',')[0]
                volumes.append(vs) # 及时记录
            # ls.sort()
            ls2 = re.findall(r'Volume [0-9]+',s)
            # 将没有issue的添加到一个列表里面，后期去重
            ls2 = set(ls2)
            ls2 = list(ls2)
            for v in ls2:
                only_volume.append(v)
            print('ok')
        # 去重复

        for v in only_volume:
            if v not in volumes:
                self.volumn_list.append(v)

        # print(sorted(self.volumn_list))
        # print(self.volumn_list)

    '''
        生成所有期刊的文章信息
    '''

    def get_all_volumes_url(self):
        article_url_dic = {}
        url_list = []
        num_list = []
        # 获取所有网站网址
        for l in self.volumn_list:
            if l.find('Issue') != -1 or l.find('Part')!=-1:
                ls = l.split(' ')
                vol = ls[1][:-1]
                vol_str = int(vol)
                issue = ls[3][:] # 注意如果不是这种形式赋值，那么两个list会同时变化
                issue_num = int(issue)
                if vol_str in article_url_dic.keys():
                    article_url_dic[vol_str].append(issue_num)
                else:
                    article_url_dic[vol_str] = []
                    self.result_dic['Volume '+str(vol_str)] = {}
                    article_url_dic[vol_str].append(issue_num)
            else:
                # for l in self.volumn_list:
                num = l.split(' ')[1]
                num_list.append(int(num))
        # print(url_list)
        # 处理有issue的
        for key in sorted(article_url_dic.keys()):
            Max = max(article_url_dic[key])
            Min = min(article_url_dic[key])
            for i in range(1,Max+1):
                url = 'https://www.sciencedirect.com/journal/'+self.title+'/vol/'+str(key)+'/issue/' + str(i)
                # 将此时的数据加到result dic中
                issue_str = 'Issue ' + str(i)
                self.result_dic['Volume '+str(key)][issue_str] = {}
                self.result_dic['Volume '+str(key)][issue_str]['url'] = url
                url_list.append(url)
                print('Volume '+ str(key) + ' ,'+'Issue ' + str(i))
        # 处理没有issue的
        for num in sorted(num_list):
            l = 'Volume ' + str(num)
            url = 'https://www.sciencedirect.com/journal/'+self.title+'/vol/'+str(num)+'/suppl/C'
            self.result_dic[l] = {}
            self.result_dic[l]['No issue'] = {}
            self.result_dic[l]['No issue']['url'] = url
            print(l)
            url_list.append(url)
        # 处理没有添加进来的
        print('#####接下来处理没有添加的内容#####')
        flag = int(input('是否存在没有添加进来的（1:是，0:否）：'))
        if flag==1:
            while True:
                supV = input('Volume(没有就输入0):')
                if supV == '0':
                    break
                k1 = 'Volume ' + str(supV)
                supI = input('Issue(没有就输入0):')
                if supI == '0':
                    url = 'https://www.sciencedirect.com/journal/'+self.title+'/vol/'+supV+'/suppl/C'
                    k2 = 'No issue'
                    if k1 in self.result_dic.keys():
                        print('已经添加过了')
                        continue
                    else:
                        self.result_dic[k1] = {}
                        print('添加成功')
                    self.result_dic[k1][k2] = {}
                    self.result_dic[k1][k2]['url'] = url
                    url_list.append(url)
                else:
                    url = 'https://www.sciencedirect.com/journal/'+self.title+'/vol/'+supV+'/issue/' + supI
                    k2 = 'Issue ' + str(supI)
                    if k1 in self.result_dic.keys():
                        if k2 in self.result_dic[k1].keys():
                            print('已经添加过了')
                            continue
                    else:
                        self.result_dic[k1] = {}
                        print('添加成功')

                    self.result_dic[k1][k2] = {}
                    self.result_dic[k1][k2]['url'] = url
                    url_list.append(url)

        self.count_issues = len(url_list)
        # 测试
        # for i in url_list:
        #     print(i)
        return url_list

    # 给定所有的期刊url，获取当前期刊下面的所有文章的url
    def get_all_articls_url(self,k1,k2):
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/80.0.3987.162 Safari/537.36'}
        article_tags = []  # 记录所有文章的编号
        times = 0
        url = self.result_dic[k1][k2]['url']
        try:
            Re = requests.get(url, headers=headers)
        except:
            print('访问volume时产生异常')
            return
        soup = BeautifulSoup(Re.text, 'html.parser')
        # 获取所有期刊的发表时间
        title = soup.find_all('title')[0]
        s = re.findall(self.time_raw, title.string)
        # print(s)
        t = ''
        if s:
            t = ' '.join(s[0]) # 获取题目信息，因为得到的是元组类型
        else:
            t = 'not find'
        self.result_dic[k1][k2]['publish time'] = t  # 存取信息
        button = soup.find_all('a', 'anchor article-content-title u-margin-xs-top u-margin-s-bottom')
        if button == []:
            return
        for bu in button:
            # print(bu.attrs['aria-describedby'])
            article_id = bu.attrs['id']
            # print(article_id)
            self.result_dic[k1][k2][article_id] = {}
            self.count_articles = self.count_articles + 1

    '''
        现在已经获取到了期刊下面的所有论文的唯一id
        需要通过这个唯一id，提取出来下面的信息：
        * 文章标题
        * 文章Received时间、文章Revised时间、文章Accepted时间、文章Available Online文章
    '''

    def get_articles_info(self,k1, k2, article_id):
        # pbar = tqdm(total=self.count_articles)
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36(KHTML, like Gecko) Chrome/80.0.3987.162 Safari/537.36'}
        # for k1 in self.result_dic.keys():
        #     for k2 in self.result_dic[k1].keys():
        #         for article_id in self.result_dic[k1][k2].keys():
        if article_id in ['url','publish time']:  # 因为字典里面有一个期刊的url
            return
        url = 'https://www.sciencedirect.com/science/article/pii/' + article_id
        # print('开始获取文章: ' + article_id)
        try:
            Re = requests.get(url, headers=headers)
        except:
            print('访问article时候出错')
            return
        soup = BeautifulSoup(Re.text, 'html.parser')
        # 获取文章标题
        meta = soup.find_all('meta')
        for m in meta:
            if 'name' in m.attrs.keys():
                if m.attrs['name'] == 'citation_title':
                    self.result_dic[k1][k2][article_id]['Article Title'] = m.attrs['content']

        # 获取文章四个时间点
        tar_ls = soup.find_all(type='application/json')
        tar_s = ''.join(tar_ls[0])  # 转换成字符串
        ls1 = re.findall(r"\"Available online\":\"[0-9]{1,2} [A-Za-z]{3,9} [0-9]{4}\"", tar_s)
        if ls1:
            s2 = ''.join(ls1)
            s3 = s2.split('\"')
            self.result_dic[k1][k2][article_id]['Available online'] = s3[-2]
        else:
            self.result_dic[k1][k2][article_id]['Available online'] = 'Not given'

        ls2 = re.findall(r"\"Received\":\"[0-9]{1,2} [A-Za-z]{3,9} [0-9]{4}\"", tar_s)
        if ls2:
            s2 = ''.join(ls2)
            s3 = s2.split('\"')
            self.result_dic[k1][k2][article_id]['Reveived'] = s3[-2]
        else:
            self.result_dic[k1][k2][article_id]['Reveived'] = 'Not given'

        ls3 = re.findall(r"\"Revised\":\[\"[0-9]{1,2} [A-Za-z]{3,9} [0-9]{4}\"\]", tar_s)
        if ls3:
            s2 = ''.join(ls3)
            s3 = s2.split('\"')
            self.result_dic[k1][k2][article_id]['Revised'] = s3[-2]
        else:
            self.result_dic[k1][k2][article_id]['Revised'] = 'Not given'

        ls4 = re.findall(r"\"Accepted\":\"[0-9]{1,2} [A-Za-z]{3,9} [0-9]{4}\"", tar_s)
        if ls4:
            s2 = ''.join(ls4)
            s3 = s2.split('\"')
            self.result_dic[k1][k2][article_id]['Accepted'] = s3[-2]
        else:
            self.result_dic[k1][k2][article_id]['Accepted'] = 'Not given'
        # 获取文章摘要
        abstract = soup.find_all('h2', 'section-title u-h3 u-margin-l-top u-margin-xs-bottom')
        for a in abstract:
            if a.string == 'Abstract':
                self.result_dic[k1][k2][article_id]['Abstract'] = str(a.next_sibling.contents[0])
        # 获取文章关键字 这个有一个div的类型是‘keyword’，可以直接获取其中的内容
        keywords = soup.find_all('div', 'keyword')
        keywords_list = []
        for key in keywords:
            keywords_list.append(key.string)
        self.result_dic[k1][k2][article_id]['keywords'] = keywords_list  # 如果为空就说明是没有

        # pbar.update(1)  # 更新进度条

        # self.write_to_json()

    '''
    现在已经得到了完整的数据字典，需要转换成excel
    '''

    def dic_to_excel(self):
        export_list = []  # 最后处理的列表
        # if dic_file != '':
        #     with open(dic_file) as f:
        #         self.result_dic = json.load(f)
        for vol in self.result_dic.keys():
            for isu in self.result_dic[vol].keys():
                for article_id in self.result_dic[vol][isu].keys():
                    if article_id == 'url' or article_id == 'publish time':
                        continue
                    if self.result_dic[vol][isu][article_id]:
                        one_dic = {}  # 因为最后是要转换成为一个大的字典列表
                        one_dic['Volume'] = vol
                        one_dic['Issue'] = isu
                        one_dic['Publish Time'] = self.result_dic[vol][isu]['publish time']
                        # one_dic['Issue Publish Time'] = self.result_dic[vol][isu]['publish time']
                        one_dic['Article_id'] = article_id
                        for info_title, info in self.result_dic[vol][isu][article_id].items():
                            # 这里面主要有文字的标题、时间数据、摘要和关键词,其中时间数据需要处理
                            one_dic[info_title] = info
                        export_list.append(one_dic)
                    else:
                        continue
        # 开始处理最后的excel
        pf = pd.DataFrame(export_list)
        order = ['Volume', 'Issue', 'Publish Time','Article_id', 'Article Title', 'Available online', 'Reveived', 'Revised',
                 'Accepted', 'Abstract', 'keywords']
        pf = pf[order]
        name = self.title + '.xlsx'
        file_path = pd.ExcelWriter(name)
        pf.fillna(' ', inplace=True)
        # 输出
        pf.to_excel(file_path, encoding='utf-8', index=False)
        file_path.save()
        print('已经写入当前文件夹的’'+name+'‘文件')


if __name__ == "__main__":  # name指向调用者，如果直接运行当前模块，那么就会作为main执行，其他模块调用则不当作main对待
    journal = input('请输入想要获取的期刊(请用journal的网页url上的名字):')
    sc = ScienceDirect(journal)
    sc.inter_journal()
    sc.get_volume()
    ls = sc.get_all_volumes_url()
    # print(ls)
    thread_num = input('请输入您想要创建的进程数量（建议4～8）：')
    thread_num = int(thread_num)
    pbar2 = tqdm(total = sc.count_issues)
    workQueus2 = queue.Queue()
    for vol in sc.result_dic.keys():
        for iss in sc.result_dic[vol].keys():
            id = []
            id.append(vol)
            id.append(iss)
            workQueus2.put(id)
    threads = []
    for i in range(1,thread_num+1):
        # print('开始创建进程')
        thread = myThread2('Thread-' + str(i),q = workQueus2,sc = sc,bar = pbar2)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    # sc.get_all_articls_url(int(n))
    sc.write_to_json()
    print('开始获取文章内容')
    pbar = tqdm(total = sc.count_articles)
    workQueus = queue.Queue()
    for vol in sc.result_dic.keys():
        for iss in sc.result_dic[vol].keys():
            for article_id in sc.result_dic[vol][iss].keys():
                id = []
                id.append(vol)
                id.append(iss)
                id.append(article_id)
                workQueus.put(id) #加入队列
                # print('获取队列成功')
    threads = []
    # print('成功创建队列')
    for i in range(1,thread_num+1):
        # print('开始创建进程')
        # 创建四个线程
        thread = myThread("Thread-"+str(i), url_q=workQueus,sc = sc, bar=pbar)
        # 开启新的线程
        thread.start()
        threads.append(thread)

    for thread in threads: # 等待进程完成
        thread.join()
    sc.write_to_json()
    sc.dic_to_excel()

