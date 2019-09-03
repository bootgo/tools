#!/usr/bin/python
# coding: utf-8

import time
import os
import sys
import platform
import shlex
import subprocess
import json
from prettytable import PrettyTable



rwResult={}

def bash(cmd):
    """
    run a bash shell command
    执行bash命令
    """
    return shlex.os.system(cmd)


def color_print(msg, color='red', exits=False):
    """
    Print colorful string.
    颜色打印字符或者退出
    """
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'yellow': '\033[1;33m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m',
                 'title': '\033[30;42m%s\033[0m',
                 'info': '\033[32m%s\033[0m'}
    msg = color_msg.get(color, 'red') % msg
    print(msg)
    if exits:
        time.sleep(2)
        sys.exit()
    return msg


def printResult():
    table = PrettyTable(["项目", "写IOPS","写带宽","读IOPS","读带宽"])
    for k,v in rwResult.items():
        list = [k,v["write_iops"],v["write_bw"],v["read_iops"],v["read_bw"]]
        table.add_row(list)
    color_print(table)

def Usage():
	print('''
用法： python fio.py size_4k size_128k /path/to/test_file"
参数:
      size_4k      进行4k读写测试的文件大小。
      size_128k    进行128k读写测试的文件大小。
      /path/to/test_file	测试文件读写的路径，这里是一个文件的完整路径。
	''')

class PreSetup(object):
    def __init__(self):
        self.dist = platform.linux_distribution()[0].lower()

    @property
    def _is_redhat(self):
        if self.dist.startswith("centos") or self.dist.startswith(
                "red") or self.dist == "fedora" or self.dist == "amazon linux ami":
            return True

    @property
    def _is_ubuntu(self):
        if self.dist == "ubuntu" or self.dist == "debian" or self.dist == "deepin":
            return True

    def check_platform(self):
        if not (self._is_redhat or self._is_ubuntu):
            print(u"支持的平台: CentOS, RedHat, Fedora, Debian, Ubuntu, Amazon Linux, 暂不支持其他平台安装.")
            exit()

    @staticmethod
    def check_bash_return(ret_code, error_msg):
        if ret_code != 0:
            color_print(error_msg, 'red')
            exit()

    def _set_env(self):
        #color_print('开始关闭防火墙和selinux', 'green')
        if self._is_redhat:
            os.system("export LANG='en_US.UTF-8'")
            # if self._is_centos7 or self._is_fedora_new:
            #     cmd1 = "systemctl status firewalld 2> /dev/null 1> /dev/null"
            #     cmd2 = "systemctl stop firewalld"
            #     cmd3 = "systemctl disable firewalld"
            #     bash('%s && %s && %s' % (cmd1, cmd2, cmd3))
            #     bash('localectl set-locale LANG=en_US.UTF-8')
            #     bash('which setenforce 2> /dev/null 1> /dev/null && setenforce 0')
            # else:
            #     bash("sed -i 's/LANG=.*/LANG=en_US.UTF-8/g' /etc/sysconfig/i18n")
            #     bash('service iptables stop && chkconfig iptables off && setenforce 0')

        if self._is_ubuntu:
            os.system("export LANG='en_US.UTF-8'")
            # bash("which iptables && iptables -F")
            # bash('which setenforce && setenforce 0')

    def _rpm_repo(self):
        if self._is_redhat:
            color_print('开始安装epel源', 'green')
            bash('yum -y fio python-pip')

    def _depend_rpm(self):
        color_print('开始安装依赖包', 'green')
        if self._is_redhat:
            cmd = 'yum -y install epel-release'
            ret_code = bash(cmd)
            self.check_bash_return(ret_code, "安装依赖失败, 请检查安装源是否更新或手动安装！")
        if self._is_ubuntu:
            cmd = "apt-get -y --force-yes install fio python-pip"
            ret_code = bash(cmd)
            self.check_bash_return(ret_code, "安装依赖失败, 请检查安装源是否更新或手动安装！")

    def _require_pip(self):
        color_print('开始安装依赖pip包', 'green')
        ret_code = bash('pip install prettytable')
        self.check_bash_return(ret_code, "安装依赖的python库失败！")

    def start(self):
        color_print('请务必先查看README.txt')
        time.sleep(3)
        self.check_platform()
        self._rpm_repo()
        self._depend_rpm()
        self._require_pip()
        self._set_env()


class FioTest(object):
    def __init__(self,name,filename,rw,bs,size,direct=1,iodepth=1,ioengine="libaio",runtime=60,rwmixwrite=30):
        self.name=name
        self.filename=filename
        self.direct=direct
        self.rw=rw
        self.bs=bs
        self.size=size
        self.iodepth=iodepth
        self.ioengine=ioengine
        self.runtime=runtime
        self.rwmixwrite=rwmixwrite

    def exprCmd(self):
       cmd ="fio --name="+self.name+" --rw="+self.rw+" --iodepth="+str(self.iodepth)+" --ioengine="+self.ioengine+" --thread --direct="+str(self.direct)+" --norandommap --bs="+self.bs+" --size="+self.size+" --runtime="+str(self.runtime)+" --filename="+self.filename+" --minimal --output-format=json"
       #print(cmd)
       return cmd

    def runCmd(self, cmd):
        #test=shlex.os.system(cmd)
        #print(type(test))
        #return test
        result_str = ''
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = process.stdout
        errors = process.stderr
        err = errors.read()
        if err:
            color_print("执行错误")
            color_print(err)
            os._exit(1)
        result_str = out.read().strip()
        if out:
            out.close()
        if errors:
            errors.close()

        return str(result_str)

    def explain(self, result):

        if self.rw == "read" or self.rw == "randread":
            r = json.loads(result)
            iops = r["jobs"][0]["read"]["iops"]
            bw = r["jobs"][0]["read"]["bw"]
            return iops,bw
        else:
            if self.rw == "write" or self.rw == "randwrite":
                r = json.loads(result)
                iops = r["jobs"][0]["write"]["iops"]
                bw = r["jobs"][0]["write"]["bw"]
                return iops, bw

    def expResult(self, iops, bw):
        name = ""
        rw_iops = ""
        rw_bw = ""
        rw = self.rw

        if rw == "write" or rw == "read":
            name = "seq-"+self.bs+"-"+str(self.iodepth)
            rw_iops = rw+"_iops"
            rw_bw = rw+"_bw"

        elif rw == "randwrite" or rw == "randread":
                name = "rand-"+self.bs+"-"+str(self.iodepth)
                rw_iops=rw[4:]+"_iops"
                rw_bw=rw[4:]+"_bw"
        else:
            name = "NotDefine"
            rw_iops=rw+"_iops"
            rw_bw = rw+"_bw"

        if name in rwResult.keys():
            rwResult[name][rw_iops] = iops
            rwResult[name][rw_bw] = bw
        else:
            rwResult[name]={}
            rwResult[name][rw_iops] = iops
            rwResult[name][rw_bw] = bw

    def saveResult(self):
        cmd = self.exprCmd()
        result = self.runCmd(cmd)
        iops, bw = self.explain(result)
        self.expResult(iops, bw)



if __name__ == '__main__':

    if len(sys.argv) != 4:
       Usage()
       exit(1)

    size4k = sys.argv[1]
    size128k = sys.argv[2]
    filename = sys.argv[3]

    if not os.path.isfile("/usr/bin/fio") :
        pre_setup = PreSetup()
        pre_setup.start()

    cmd1 = FioTest(name="randread-4k", rw="randread", iodepth=1, ioengine="libaio", direct=1, bs="4k", size=size4k,
                       runtime=60, filename=filename)
    cmd1.saveResult()

    cmd2 = FioTest(name="randwrite-4k", rw="randwrite", iodepth=1, ioengine="libaio", direct=1, bs="4k", size=size4k,
                        runtime=60, filename=filename)
    cmd2.saveResult()

    cmd3 = FioTest(name="randread-4k-64", rw="randread", iodepth=64, ioengine="libaio", direct=1, bs="4k", size=size4k,
                       runtime=60, filename=filename)
    cmd3.saveResult()

    cmd4 = FioTest(name="randwrite-4k-64", rw="randwrite", iodepth=64, ioengine="libaio", direct=1, bs="4k", size=size4k,
                   runtime=60, filename=filename)
    cmd4.saveResult()

    cmd5 = FioTest(name="seq-read-128k", rw="read", iodepth=64, ioengine="libaio", direct=1, bs="128k", size=size128k,
                       runtime=60, filename=filename)
    cmd5.saveResult()

    cmd6 = FioTest(name="seq-write-128k", rw="write", iodepth=64, ioengine="libaio", direct=1, bs="128k", size=size128k,
                       runtime=60, filename=filename)
    cmd6.saveResult()

    printResult()
