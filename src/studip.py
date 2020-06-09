import time
import logging as log

from tqdm import tqdm
import requests as req
from requests.auth import HTTPBasicAuth


class Studip:

    def __init__(self, chunk_size, domain, user, db):
        self.CHUNK_SIZE = chunk_size
        self.DOMAIN = domain
        self.USER = user
        self.db = db

    def auth_req(self, url):
        url = self.DOMAIN + url
        return req.get(url, auth=self.USER)

    def get_uid(self):
        rsp = self.auth_req('/api.php/user/')
        user_id = rsp.json()['user_id']
        return user_id

    def get_curr_semester(self):
        rsp = self.auth_req('/api.php/semesters/')
        curr_time = int(str(int(time.time())))
        semesters = rsp.json()['collection']
        for sem_uri in semesters:
            semester = semesters[sem_uri]
            sem_begin = semester['begin']
            sem_end = semester['end']
            if sem_begin < curr_time < sem_end:
                return sem_uri
        return 0

    def get_ordered_semesters(self):
        rsp = self.auth_req('/api.php/semesters/')
        semesters = rsp.json()['collection']
        order_sems = []
        for sem_uri in semesters:
            order_sems.append(sem_uri)
        return order_sems

    def get_curr_courses(self, user_id, semester):
        rsp = self.auth_req('/api.php/user/' + user_id + '/courses')
        ord_sems = self.get_ordered_semesters()
        courses = rsp.json()['collection']
        i = 0
        course_list = {}
        for course_uri in courses:
            course = courses[course_uri]
            start_sem = course['start_semester']
            if start_sem != None:
                start_ind = ord_sems.index(start_sem)
            else:
                start_ind = 100
            end_sem = course['end_semester']
            if end_sem != None:
                end_ind = ord_sems.index(end_sem)
            else:
                end_ind = 100
            curr_ind = ord_sems.index(semester)
            if start_ind <= curr_ind <= end_ind:
                course_title = course['title']
                course_id = course['course_id']
                course_list[course_id] = course_title
        return course_list

    def get_top_folder(self, course):
        rsp = self.auth_req('/api.php/course/' + course + '/top_folder')
        top_folder = rsp.json()
        tf_id = top_folder['id']
        return(tf_id)

    def get_docs(self, folder):
        rsp = self.auth_req('/api.php/folder/' + folder)
        docs = rsp.json()['file_refs']
        res_docs = []
        for doc in docs:
            doc_id = doc['id']
            res_docs.append(doc_id)
        return(res_docs)

    def download(self, doc):
        rsp1 = self.auth_req('/api.php/file/' + doc)
        doc_name = rsp1.json()['name']
        doc_chdate = rsp1.json()['chdate']
        last_dl = self.db.get_last_file_dl(doc)
        if last_dl == None or last_dl < doc_chdate:
            rsp2 = self.auth_req('/api.php/file/' + doc + '/download')
            total_size = int(rsp2.headers.get('content-length', 0))
            print('downloading ' + doc_name)
            progbar = tqdm(total=total_size, unit='iB', unit_scale=True)
            with open(doc_name, 'wb') as doc_file:
                for chunk in rsp2.iter_content(self.CHUNK_SIZE):
                    progbar.update(len(chunk))
                    doc_file.write(chunk)
            self.db.set_last_file_dl(str(doc), str(int(time.time())))

    def get_subdirs(self, folder):
        rsp = self.auth_req('/api.php/folder/' + folder)
        subdirs = rsp.json()['subfolders']
        docs = rsp.json()['file_refs']
        res_subdirs = {}
        for subdir in subdirs:
            sub_id = subdir['id']
            sub_name = subdir['name']
            res_subdirs[sub_id] = sub_name
        return res_subdirs
