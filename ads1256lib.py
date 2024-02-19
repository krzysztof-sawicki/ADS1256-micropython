#Micropython driver for ADS1256
# reset() - Reset ADS1256
# sync() - Synchronize the A/D conversion using SYNC pin
# select()/deselect() - Select/deselect ADS1256
# waitDRDY() - wait for DRDY to go low
# read_reg(reg_addr) - Read register with reg_addr address, return register value
# write_reg(reg_addr, data) - Write data to register reg_addr
# set_pga(PGA) - sets programmable gain amplifier
# select_channel(CH) - Select channel CH
# read_single() - Convert and read 1 shot, return converted value
# read_continuous() - Convert continuously one channel, return first converted value
# read_conversion() - Read last conversion, return conversion
# cycle_channel(CH) - Cycle to channel CH and returns value of previous channel conversion
# select_differential_channel(PCH, NCH) - Selects differential channel (+PCH-NCH)
# self_cal() - Performs self offset and gain calibration
# self_ocal() - Performs self offset calibration
# self_gcal() - Performs self gain calibration
# sys_ocal() - Performs system offset calibration
# sys_gcal() - Perfomrs system gain calibration
# standby() - Enters low-power standby mode
# wakeup() - Wakes up form standby mode

from micropython import const
import ustruct
import utime

class ADS1256:
    """ADS1256 registers"""
    STATUS=const(0x00)
    MUX=const(0x01)
    ADCON=const(0x02)
    DRATE=const(0x03)
    IO=const(0x04)
    OFC0=const(0x05)
    OFC1=const(0x06)
    OFC2=const(0x07)
    FSC0=const(0x08)
    FSC1=const(0x09)
    FSC2=const(0x0A)

    """Single-ended channels"""
    CH0=const(0x08)
    CH1=const(0x18)
    CH2=const(0x28)
    CH3=const(0x38)
    CH4=const(0x48)
    CH5=const(0x58)
    CH6=const(0x68)
    CH7=const(0x78)
    
    """Sampling rates"""
    DR2_5=const(0x03)
    DR5 = const(0x13)
    DR10=const(0x23)
    DR15=const(0x33)
    DR25=const(0x43)
    DR30=const(0x53)
    DR50=const(0x63)
    DR60=const(0x72)
    DR100=const(0x82)
    DR500=const(0x92)
    DR1K=const(0xA1)
    DR2K=const(0xB0)
    DR3_75K=const(0xC0)
    DR7_5K=const(0xD0)
    DR15K=const(0xE0)
    DR30K=const(0xD0)
    
    
    PGAMASK  = const(0x07)
    PGANMASK = const(0xF8)
    """Programmable Gain Amplifier"""
    PGA1     = const(0x00)  # x1
    PGA2     = const(0x01)  # x2
    PGA4     = const(0x02)  # x4
    PGA8     = const(0x03)  # x8
    PGA16    = const(0x04)  # x16
    PGA32    = const(0x05)  # x32
    PGA64    = const(0x06)  # x64
    
    
    def __init__(self, spi, cs, DRDY, SYNC=None, ref_voltage=5.0, pga = PGA1):
        #Define module pins and SPI interface
        self.cs=cs
        self.spi=spi
        self.ref_voltage=ref_voltage
        self.drdy=DRDY
        self.sync=SYNC
        self.pga = pga
        #Define data buffers
        self.outbuff=bytearray(1)
        self.conversion=bytearray(3)
        
        self.set_pga(pga)
        
    def select(self):
        #Select ADS slave
        self.cs.value(0)

    def deselect(self):
        #Deselect ADS slave
        self.cs.value(1)
        
    def reset(self):
        #Reset ADC, this returns all registers except CLK0 and CLK1 bits in the ADCON register to their default values.
        #This command will stop the read continuous mode
        while self.drdy.value():
            pass
        self.select()
        self.spi.write(b'\xFE') #Reset
        utime.sleep_ms(1)
        self.spi.write(b'\x0F') #Issue SDATAC
        utime.sleep_us(2)
        self.deselect()
        
    def sync(self):
        #Performs synchronization with SYNC pin
        #If SYNC pin is not given, returns False
        if(not self.sync): return False
        self.sync.value(0)
        utime.sleep_us(1)
        self.sync.value(1)      
        
    def waitDRDY(self):
        #Waits for DRDY to go low
        #If DRDY is low, conversion is available or can perform a write command
        while self.drdy.value():
            pass
        
    def read_reg(self,reg_addr):
        #Read single register and returns the values of the register
        while self.drdy.value():
            pass
        self.cs.value(0)
        buff=bytearray([0x10|reg_addr,0x00])
        self.spi.write(buff)
        utime.sleep_us(7)
        self.spi.readinto(self.outbuff,0xFF)
        self.cs.value(1)
        return self.outbuff
    
    def write_reg(self,reg_addr,data):
        #Write single register, address and data must be 1 byte values
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0x50|reg_addr,0x00]))
        self.spi.write(bytearray([data]))
        self.cs.value(1)
        
    def read_pga(self):
        return self.read_reg(self.ADCON)[0] & self.PGAMASK

    def set_pga(self, pga):
        oldpga = self.read_reg(self.ADCON)[0]
        npga = (oldpga & self.PGANMASK) | (pga & self.PGAMASK)
        self.write_reg(self.ADCON, npga)
        
    def select_channel(self, CH):
        #Select a specific single-ended channel
        self.write_reg(MUX, CH)
        
    def select_differential_channel(self, PCH, NCH):
        """
        Select a differential input (PCH - NCH)
        PCH - Positive channel
        NCH - Negative channel
        """
        ch = (PCH & 0xF0) | (NCH >> 4)
        print("Kanał: {:02x}".format(ch))
        self.select_channel(ch)
        
    def read_single(self):
        #Perform one-shot conversion and returns conversion value
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0x01])) #RDATA
        utime.sleep_us(7) #wait t6=6.51us
        self.spi.readinto(self.conversion,0xFF)
        utime.sleep_us(2) #wait t10=1.04us
        self.cs.value(1)
        return self.conversion
    
    def read_continuous(self):
        #Performs a continuous conversion of the selected channel at the specified data rate in DRATE register
        #Every time a conversion is made, DRDY goes low
        #This fuction returns the first conversion, further conversions must be read with read_conversion function
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0x03]))
        utime.sleep_us(7) #wait t6=6.51us
        self.spi.readinto(self.conversion,0xFF) #Read 3bytes
        utime.sleep_us(2) #wait t10=1.04us
        self.cs.value(1)
        return self.conversion
    
    def read_conversion(self):
        #Read last conversion. This function does not perform a conversion
        while(self.drdy.value()):
            pass
        self.cs.value(0)
        #self.conversion=self.spi.read(3)
        self.spi.readinto(self.conversion,0xFF)
        self.cs.value(1)
        return self.conversion
    
    def cycle_channel(self, CH):
        #Cycle to channel CH and returns the conversion of the previous channel
        #Cycling through channels has 3 steps (see page 21 of ADS1256 datasheet)
        self.select()
        while(self.drdy.value()):
            pass
        #Step1
        self.spi.write(bytearray([0x50|0x01,0x00])) #Write into MUX register
        self.spi.write(bytearray([CH])) 
        #Step2
        self.spi.write(bytearray([0xFC])) #SYNC
        utime.sleep_us(4) #Delay t11
        self.spi.write(bytearray([0xFF])) #WAKEUP
        #Step3
        self.spi.write(bytearray([0x01])) #RDATA
        utime.sleep_us(7) #wait t6=6.51us
        self.spi.readinto(self.conversion,0xFF) #Read 3bytes
        self.deselect()
        return self.conversion
        
    def self_cal(self):
        #Performs self offset and gain calibration
        #The Offset Calibration Register (OFC) and Full-Scale Calibration Register (FSC) are updated after this operation
        #DRDY goes high at the beginning of the calibration and goes low after calibration completes and settled data is ready. Do not send additional commands after issuing
        #this command until DRDY goes low. 
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0xF0]))
        utime.sleep_us(2) #wait t10=1.04us
        self.cs.value(1)
        
    def self_ocal(self):
        #Performs a self offset calibration. The OFC register is updated after this operation
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0xF1]))
        utime.sleep_us(2) #wait t10=1.04us
        self.cs.value(1)
        
    def self_gcal(self):
        #Performs a self gain calibration. The FSC register is updated with new values after this operation
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0xF2]))
        utime.sleep_us(2) #wait t10=1.04us
        self.cs.value(1)
        
    def sys_ocal(self):
        #Performs a system offset calibration. The OFC register is updated after this operation
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0xF3]))
        utime.sleep_us(2) #wait t10=1.04us
        self.cs.value(1)
        
    def sys_gcal(self):
        #Performs a system gain calibration. The FSC register is updated after this operation
        while self.drdy.value():
            pass
        self.cs.value(0)
        self.spi.write(bytearray([0xF4]))
        utime.sleep_us(2) #wait t10=1.04us
        self.cs.value(1)
        
    def standby(self):
        #This command puts the ADC into a low-power Standby mode.
        self.select()
        self.spi.write(bytearray([0xFD])) #Begin standby mode command
        self.deselect()
        
    def wakeup(self):
        #This command wakes up the ADC from standby mode
        self.select()
        self.spi.write(bytearray([0xFF])) #Wakeup command
        self.deselect()
        


