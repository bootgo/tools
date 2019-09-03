package main

import (
	"fmt"
	"github.com/bitly/go-simplejson"
	"github.com/syohex/go-texttable"
	"os"
	"os/exec"
	"strconv"
)

type fioArgs struct {
	filename string
	direct int
	rw string
	bs string
	bsrange string
	size string
	iodepth int
	ioengine string
	numjobs int
	runtime int
	rwmixwrite int
	lockmem string
	name string
}

func (c *fioArgs) expCmd() string {
	cmd :=fmt.Sprintf("fio --name=%s --rw=%s --iodepth=%d --ioengine=%s --thread --direct=%d --norandommap 	--bs=%s --size=%s --runtime=%d --filename=%s --minimal --output-format=json",c.name,c.rw,c.iodepth,c.ioengine,c.direct,c.bs,c.size,c.runtime,c.filename)
	return cmd
}

func (c *fioArgs) runCmd(strCommand string) ([]byte, error){
	cmd := exec.Command("bash","-c",strCommand)
	out, err := cmd.Output()
	if err != nil {
		return nil,err
	}

	return out,nil

}

func (c *fioArgs) expResult(out []byte)(float64,float64){
	jsOut, err := simplejson.NewJson(out)
	if err != nil {
		panic(err.Error())
	}

	p:=jsOut.Get("jobs").GetIndex(0)

	//personArr:= js.Get("jobs").Array()

	switch c.rw {
	case "read","randread":
		iops := p.Get("read").Get("iops").MustFloat64()
		bw := p.Get("read").Get("bw").MustFloat64()
		return iops,bw
	case "write","randwrite":
		iops := p.Get("write").Get("iops").MustFloat64()
		bw := p.Get("write").Get("bw").MustFloat64()
		return iops,bw
	default:
		fmt.Print("参数错误")
		return 0,0
	}

}

func (c *fioArgs) saveResult(iops,bw float64){
	var fName, iopsName, bwName string
	switch c.rw {
	case "read","write":
		fName = "seq-"+c.bs+"-"+strconv.Itoa(c.iodepth)
		iopsName = c.rw+"iops"
		bwName = c.rw+"bw"

	case "randread","randwrite":
		crw := c.rw[4:]
		fName = "rand-"+c.bs+"-"+strconv.Itoa(c.iodepth)
		iopsName = crw+"iops"
		bwName = crw+"bw"
	default:
		fName = "NotDefine"
		iopsName = c.rw+"iops"
		bwName = c.rw+"bw"
	}

	_,ok := resultIn[fName]
	if ok{
		resultIn[fName][iopsName]=iops
		resultIn[fName][bwName]= bw
	}else {
		r := make(map[string]float64)
		r[iopsName]= iops
		r[bwName] = bw
		resultIn[fName] = r
	}

}


func (c * fioArgs) startFio(){
	cmd := c.expCmd()
	out,err := c.runCmd(cmd)
	if err != nil{
		fmt.Println("执行fio测试错误")
		os.Exit(1)
	}
	iops,bw := c.expResult(out)
	c.saveResult(iops,bw)

}


var resultIn = make(map[string]map[string]float64)


func printResult(){
	tbl := &texttable.TextTable{}
	err := tbl.SetHeader("项目", "写IOPS","写带宽","读IOPS","读带宽")
	if err != nil{
		panic(err)
	}

	for k,v := range resultIn{
		wIops := fmt.Sprintf("%f",v["writeiops"])
		wBw := fmt.Sprintf("%.0f",v["writebw"])
		rIops := fmt.Sprintf("%f",v["readiops"])
		rBw := fmt.Sprintf("%.0f",v["readbw"])

		err := tbl.AddRow(k,wIops,wBw,rIops,rBw)
		if err!= nil{
			panic(err)
		}
	}

	fmt.Println(tbl.Draw())
}

func PathExists(path string) (bool, error) {
	_, err := os.Stat(path)
	if err == nil {
		return true, nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, err
}

func main(){

	ex ,_ := PathExists("/usr/bin/fio")
	if !ex{
		fmt.Println("没有检测到/usr/bin/fio命令，请先安装fio")
		os.Exit(1)
	}

	args := os.Args

	if len(args) != 4 {
		Usage()
		os.Exit(1)
	}
	fioPath := args[3]
	size4k := args[1]
	size128k := args[2]

	var c1 =fioArgs{name:"randread-4k",rw:"randread",iodepth:1,ioengine:"libaio",direct:1,bs:"4k",size:size4k,runtime:60,filename:fioPath}
	var c2 =fioArgs{name:"randread-4k-64",rw:"randread",iodepth:64,ioengine:"libaio",direct:1,bs:"4k",size:size4k,runtime:60,filename:fioPath}
	var c3 =fioArgs{name:"randwrite-4k",rw:"randwrite",iodepth:1,ioengine:"libaio",direct:1,bs:"4k",size:size4k,runtime:60,filename:fioPath}
	var c4 =fioArgs{name:"randwrite-4k-64",rw:"randwrite",iodepth:64,ioengine:"libaio",direct:1,bs:"4k",size:size4k,runtime:60,filename:fioPath}
	var c5 =fioArgs{name:"seq-read-128k",rw:"read",iodepth:64,ioengine:"libaio",direct:1,bs:"128k",size:size128k,runtime:60,filename:fioPath}
	var c6 =fioArgs{name:"seq-write-128k",rw:"write",iodepth:64,ioengine:"libaio",direct:1,bs:"128k",size:size128k,runtime:60,filename:fioPath}

	c1.startFio()
	c2.startFio()
	c3.startFio()
	c4.startFio()
	c5.startFio()
	c6.startFio()

	printResult()
}

func Usage(){
	fmt.Print(
		`
用法： ./fio size_4k size_128k /path/to/test_file"
参数:
   size_4k      进行4k读写测试的文件大小,如100M。
   size_128k    进行128k读写测试的文件大小,如200M。
   /path/to/test_file	测试文件读写的路径，这里是一个文件的完整路径，如/tmp/tmp1g.iso。

`)
}
