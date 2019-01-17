# f2_interpolator class 
# Last modification by Marko Kosunen, marko.kosunen@aalto.fi, 16.11.2018 14:13
# Add TheSDK to path. Importing it first adds the rest of the modules
import os
import numpy as np

from thesdk import *
from verilog import *
from cic3_interpolator import *
from halfband_interpolator import *

class f2_interpolator(verilog,thesdk):
    @property
    def _classfile(self):
        return os.path.dirname(os.path.realpath(__file__)) + "/"+__name__

    def __init__(self,*arg): 
        self.proplist = [ ' '];    #properties that can be propagated from parent
        self.Rs_high = 8*160e6;    # sampling frequency
        self.Rs_low=20e6
        self.BB_bandwidth=0.45
        self.iptr_A = IO();
        self.model='py';           #can be set externally, but is not propagated
        self.export_scala=False    # Be careful with this
        self.scales=[1,1,1,1]
        self.cic3shift=0
        self._filters = [];
        self._Z = IO();
        self.zeroptr=IO()
        self.zeroptr.Data=np.zeros((1,1))
        if len(arg)>=1:
            parent=arg[0]
            self.copy_propval(parent,self.proplist)
            self.parent =parent;
        self.init()

    def init(self):
        self.mode=self.determine_mode()                 
        #self._vlogmodulefiles=list(["clkdiv_n_2_4_8.sv"])                 
        #self.def_verilog()
        #self._vlogparameters=dict([ ('g_Rs_high',self.Rs_high), ('g_Rs_low',self.Rs_low), 
        #    ('g_scale0',self.scales[0]),  
        #    ('g_scale1',self.scales[1]),  
        #    ('g_scale2',self.scales[2]),  
        #    ('g_scale3',self.scales[3]),
        #    ('g_cic3shift',self.cic3shift),
        #    ('g_mode',self.mode)
        #    ])

    def run(self,*arg):
        if len(arg)>0:
            self.par=True      #flag for parallel processing
            self.queue=arg[0]       #multiprocessing.Queue as the first argument
        else:
            self.par=False

        #Example of how to use Python models for sub-blocks, but
        #Merged verilog for the current modeule
        if self.model=='py':
            self.main()
        else: 
          self.write_infile()
          self.run_verilog()
          self.read_outfile()

    def main(self):
        if self.mode>0:
            self.generate_interpolator()
            for i in range(len(self._filters)):
                self._filters[i].run()
                self._filters[i]._Z.Data=(self._filters[i]._Z.Data*self.scales[i]).reshape(-1,1)
            out=self._filters[-1]._Z.Data
        else:
            out=self.iptr_A.Data
        if self.par:
            self.queue.put(out)
        maximum=np.amax([np.abs(np.real(out)), np.abs(np.imag(out))])
        str="Output signal range is %i" %(maximum)
        self.print_log(type='I', msg=str)
        self._Z.Data=out

    def generate_interpolator(self,**kwargs):
       n=kwargs.get('n',np.array([40,8,6]))
       self._filters=[]
       for i in range(self.mode):
           if i==3:
               h=cic3_interpolator()
               h.Rs_high=self.Rs_high
               h.Rs_low=self.Rs_low*8
               h.derivscale=self.scales[3]
               h.cic3shift=self.cic3shift
               h.init()
           else:
               h=halfband_interpolator()
               h.halfband_Bandwidth=self.BB_bandwidth/(2**i)
               h.halfband_N=n[i]
               h.Rs_high=self.Rs_low*(2**(i+1))
               h.init()
               if self.export_scala:
                   h.export_scala()
           self._filters.append(h)

       #Here, in order to model multiplier, we would need to 
       # Create multiplier instance with pointers
       for i in range(len(self._filters)):
           if i==0:
               self._filters[i].iptr_A=self.iptr_A
           else:
               self._filters[i].iptr_A=self._filters[i-1]._Z
           self._filters[i].init()

    def determine_mode(self):
        #0=bypass, 1 interpolate by 2, 2 interpolate by 4, 
        #3 interpolate by 8, 4, interpolate by more
        M=self.Rs_high/self.Rs_low
        if (M%8!=0) and (M!=4) and (M!=2) and (M!=1):
            self.print_log(type='F', msg="Interpolation ratio is not valid. Must be 1,2,4,8 or multiple of 8")
        else:
            if M<=8:
                mode=int(np.log2(M))
            else:
             mode=int(4)
        self.print_log(type='I', msg="Interpolation ratio is set to %i corresponding to mode %i" %(M,mode))
        return mode

if __name__=="__main__":
    import matplotlib.pyplot as plt
    from  f2_interpolator import *
    t=thesdk()
    t.print_log({'type':'I', 'msg': "This is a testing template. Enjoy"})
