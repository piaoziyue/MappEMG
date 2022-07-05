
from os import system
import numpy as np


from biosiglive.interfaces.bitalino_interface import BitalinoClient
# from biosiglive.processing.data_processing import RealTimeProcessing
from biosiglive.gui.plot import LivePlot
from biosiglive.processing.mappEMG import Mapper
from biosiglive.processing.mappEMG import EMGprocess
from biosiglive.processing.mappEMG import Emitter
from time import sleep, time


if __name__ == '__main__':

    print("\nWelcome to the Bitalino example...")
    print("\nThe macAddress variable on Windows can be \"XX:XX:XX:XX:XX:XX\" or \"COMX\" \n while on Mac OS can be \"/dev/tty.BITalino-XX-XX-DevB\"")
    #address_bitalino = input("\nBitalino Address (leave empty if \"/dev/tty.BITalino-7E-19-DevB\"): ")
    address_bitalino = input("\nBitalino Address (leave empty if \"/dev/tty.BITalino-1E-10-DevB\"): ")
    #
    # save = input()
    if address_bitalino == "":
        address_bitalino = "/dev/tty.BITalino-1E-10-DevB"
    try:
        bitalino_interface = BitalinoClient(ip=address_bitalino)
    except:
        print("Could not create Bitalino Client. Possibly bad address")
    
    # set acquisition channels
    acq_channels = input("\nEnter list of acquisition channels (e.g. for A1 A2 A3, write 1 2 3): ").split(" ")
    #acq_channels = acq_channels.split(" ")
    for i in range(len(acq_channels)):
        acq_channels[i] = int(acq_channels[i]) - 1

    n = len(acq_channels)
    # initializing weights
    weights_raw = input("\nAttribute weights between 0 and 1 to each sensor (e.g for A1 A2 A3, write 0.45 1 0): ").split(" ")
    while len(weights_raw) != n:
        print("\nNumber of weights does not correspond to number of channels")
        weights_raw = input("\nAttribute weights between 0 and 1 to each sensor (e.g for A1 A2 A3, write 0.45 1 0): ").split(" ")
    
    weights = np.empty((1,n))
    for i, w in enumerate(weights_raw):
        weights[0][i] = float(w)
    
    # set sampling rate
    rate = int(input("\nEnter sampling rate (1, 10, 100, or 1000): ")) # 2000
    system_rate = rate//20 # 100
    if system_rate == 0:
        system_rate = 1
    
    # initializing post processors for each sensor & mapper
    post_processors = dict()
    for i in range(0,n):
        post_processors[i] = EMGprocess()


    mapper = Mapper(n,system_rate) 

    # initializing phones to which we send the haptics
    emitter = Emitter()
    n_devices = input('\nHow many devices with the haptics app would you like to connect? ')
    n = 1
    while n != int(n_devices)+ 1:
        ip = input(f'\nIP of device number {n} (e.g: XXX.XXX.X.X): ')
        port = input(f'\nPORT of device number {n} (e.g: 2222): ')
        ip = str(ip)
        port = int(port)
        try:
            emitter.add_device_client(ip,port)
            n = n + 1
        except:
            print("Invalid IP or PORT, try again...")


    
    # def add_device(self, name: str = None, rate: int = 1000, system_rate: int = 100, acq_channels: list = [1,2,3,4,5,6]):
    bitalino_interface.add_device("Bitalino", rate=rate, system_rate=system_rate, acq_channels=acq_channels)

    plot_app = LivePlot()
    plot_app.add_new_plot("EMG", "curve", ["A1", "A2"])
    rplt, window, app, box = plot_app.init_plot_window(plot=plot_app.plot[0], use_checkbox=True)


    run = True


    while run:
        bitalino_interface.start_acquisition()
        #print()
        n_frames = 0
        
        while n_frames < 10000:


            data_tmp = bitalino_interface.get_device_data(device_name="Bitalino")[0]
            #print(np.shape(data), data)
            #print(np.shape(data_tmp),data_tmp)
            print('in bits', data_tmp, np.shape(data_tmp))
            data_tmp = (data_tmp/(2**10)-0.5)*3.3/1009*1000 # converting bits to mV
            print('pre processed', data_tmp, np.shape(data_tmp))
            
            for i in range(0,n):
                for j in range(0,len(data_tmp[i])):

                    ##### PROCESSING ######
                    post_processors[i].input(data_tmp[i][j]) # inputting data to be processed (data_tmp is a 1 x 1 matrix, thus [0][0] to obtain val)
                    post_processors[i].clip() # clipping data in case it is not between 0 and 1
                    post_processors[i].slide() # sliding/smoothing the data
                    #post_processors[i].scale(0.4) # commenting this out because right now there are values bigger than .4
                    data_tmp[i][j] = post_processors[i].x_emg_scaled

            
            
            data = data_tmp if n_frames == 0 else np.append(data, data_tmp, axis=1)
            #print(data)
            plot_data = data if n_frames*system_rate < 5*rate else data[:, -5*rate:]
            plot_app.update_plot_window(plot_app.plot[0], plot_data, app, rplt, box)

            ##### MAPPING  & EMITTER #####
            mapper.input(data_tmp)
            weighted_avr = mapper.weighted_average(weights)
            for w in weighted_avr[0]:
                emitter.sendMessage(mapper.toFreqAmpl(w))
           
            n_frames += 1

        bitalino_interface.stop_acquisition()
        print("\nEND\n")
        run = bool(input("Read again? "))
                        

