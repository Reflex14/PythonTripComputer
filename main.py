#!/usr/bin/python3

""" Boardcomputer fan De Genieter

    In script om de elektroanika oan te stjoeren op in slimme manier
    Dit script is makke foar de raspberry pi, mar kin op elke pc my python fêst draaie

    Bedoeld om in microcontroller lykas in Arduino oan te stjoeren

    De Arduino hat net alle mooglikheden as in Raspberry om te communiceren my wifi/skermen/bluetooth
    Maar de Raspberry kin dan wer net op sinjaal nivo de apparatuer oan stjoere, zonder
    dat wy dêr wer djoere dingen foar oan skafje matte

    Sa bringe wy de ferwurkingskrêft fan de raspberry en de betrouberens en elektryske kracht
    fan in microcontroller as in Arduino by inoar
"""

# Alderwertske seriele kommunikaasje foar python
from serial import *

# Wy matte altyd in bytsje tiid frij meitsje om in koeske te dwaan
from time import sleep

# In apart triedsje meitsje wy oan om apart fan ûs programma gegevens te krijen fan de Arduino
# Sa hawwe yn dit Python script twa, of mear kin ek natuurlijk, programma's draaien in ien script
# Sa meitsje wy et makkelijker om wat moais te meitsjen my ûs eigen gerommel yn het main() proses
from threading import Thread, Event

# Hjir kin wy de CTRL-C en KILL sinjalen fan et bestjoeringssysteem my harkje
# Sa ha wy sels de macht om goed of te slúten en nog krekt wat dinkjes te regelen foar
# dat wy de boel âfsluute, as wy dan ek mar ofslúte, et bestjoeringssysteem mat yn it gefal
# dat er wat is, lykas in reboot of in geheugen probleem, de macht hâlde om het programma te slûten
import signal

"""Ynstellings dy wy makkelijk even feroarje kinne"""

# Seriële poart wêr dat de Arduino oan hinget
# Dizze kin wol es feroarje ast dat ding te snel oppenei yn in USB gotsje stekkest
# Dan krijt er bygelyks wol es de namme /dev/ttyUSB1
arduino_port = "/dev/ttyUSB0"

# De snelhiet fan de kommunikaasje tussen de Arduino en dizze computer
# Dit kinst feroarje, et kin nog folle flucher fansels ...
# Maar dizze snelhiet mat geliek wêze oan de ynstellings fan de Arduino
# Dus net oanpasse ast et op de Arduino ek net oanpast!
#
# Standert ynstelling foar de meeste seriële apparaten is 9600
# Dus dat hak mar sa litten
#
# De Arduino kin mei in snelhiet fan 115200 oan de skieterij wêze, hoe
# moai dat ek is, dot is tink ik mear om realtime gegevens te sammeljen.
# En dêr broeke wy it spul net foar.
#
# Dus 9600 is mear as genôch. En in legere snelhiet is bygelyks minder gefoelich
# foar eksterne steursinjalen dy't ûs dreech meitsje om it saakje ût te lêzeb.
arduino_baudrate = 9600

# Wy meitsje de stapel commando's, dy't wy ontvangen hieden, nei in skoftke wer skjin.
# Dan bin wy dêr wis fan dat it saakje sien geheugen net op brûkt as wy dit
# programma in skoftsje oan stean litte
command_timeout = 5.0


class ReceiverJob(Thread):
    """ In wurker wêr dat wy de status en kommando's wer werom mei krije van de Arduino
        Hjir meitsje wy yn it haadprogramma (main()) in apart kuierend triedsje fan
    """

    def __init__(self, serial, seconds_to_keep_commands):
        """ Dit is de constructor fan it beestje
            Dit brûkst om dizze kloat oan te meitsjen en wer dûdelijk
            is wot er noadig is fan dy om it wurkjende te krijgen
            En dot bin de folgjende parameters:

            Parameters:
            serial (Serial):                It "Serial" objekt, ût de pySerial biblioteek (brûk "pip install pyserial")
            seconds_to_keep_commands (int): Hoe lang in sekonden dat wy de kommando's ophoopje
        """
        Thread.__init__(self)

        self.serial = serial
        self.byte_buffer = bytearray()
        self.serial_port_available = True
        self.unrecoverable_error = False
        self.seconds_to_keep_commands = seconds_to_keep_commands

        # Wy hawwe spitigernôch gjin iepenbare en privee mooglikheden in python
        # Ik haw dizze fariabelen mar even apart setten mei dit kommentaar.
        # Dizze binne bedoeld om ût te lêzen troch it haadtriedsje (main())
        # Hjir kin wy dus wat mei, de fariabelen hjir boppe rêd it beestje hjir sels mei
        self.arduino_answers = {}
        self.last_status = ''

        # Dizze is net belangryk foar wat wy noadig binne,
        # Mar ik set it hjir even del om dat dizze eins ek iepenbaar is
        # Dizze brûke wy yn it gefal dat wy afslûte wolle of dêr is in oare reden om
        # dit triedsje te stopjen
        # In apart triedsje kin ommers gjin sinjalen ontvangen fan het bestjoeringssysteem
        # Dizze sinjalen krijt het haadproses (main()), mar it haadproses kin efter dat it sa'n
        # sinjaal krijt, dit flagje oanpasse, sa dat it triedsje wiet dat er ofslúte mat, sa
        # kin er sien spultsje nog even ôfmeitsje, wy brûke dêr dit kommando foar yn het
        # haadproses (main()):
        #
        # hoest_dizze_klasse_ek_mar_oan_makke_hiedest.shutdown_flag.set()
        self.shutdown_flag = Event()

    def run(self):
        # Wy stopje net earder dan dat wy de oarder krije om de geest te jaan
        while not self.shutdown_flag.is_set():
            try:
                # Wy stopje ûs bufferke vol mei all wat et bestjoeringssysteem foar
                # ûs sammelje hat, fan de seriële keppeling mei de Arduino
                self.byte_buffer.extend(self.serial.read(self.serial.inWaiting()))

                # Even sliepe, oars hat et processorke gjin tiit meer foar oare dingen
                sleep(0.01)
            except SerialException:
                # Hjir gjit et mis mei de keppeling, kin komme troch dast er mei dien
                # brieke klauwen oan sist, mar kin ek wêze dat in oar programma ûs poart
                # stellen hat
                #
                # Wy soargje d'r hjir foar dat wy rinnende bliuwe en besykje de keppeling
                # werom te heljen
                self.serial_port_available = False

                # Wy witte net hoe lang dat d'r fjot wêst is, wy meitsje de buffers skjin
                # Dat sil fêst net meer klopje, tinkst al?
                self.arduino_answers = {}
                self.last_status = ''
                self.byte_buffer = bytearray()

                # No kin wy de keppeling slúte
                self.serial.close()

                # En wachtsje wy wer tot er d'r wer is
                while not self.serial_port_available:
                    try:
                        for x in range(10, 0, -1):
                            sleep(1)
                            print('\rWe starte de seriële bende wer oer san '
                                  + str(x) + ' seconden       ', end="", flush=True)

                        # Wy iepenje et saakje wyr, en at d'r nog net beskikber is, dan
                        # goait er in útsundering (SerialException), en krije wy ús printsje
                        # dat er d'r wer is net te sjen
                        self.serial.open()
                        print('\rSeriële poarte idder, wy gjin wer troch ...     ')

                        self.serial_port_available = True
                    except SerialException:
                        print("\rSeriële poart idder nog steeds net boeke ....     ", end="", flush=True)

                continue
            except OSError:
                # Dizze útsundering hie ik fan ferwachte dat er fangt wêze soe troch
                # de SerialException, docht er net, dus fange wy et sels mar op
                # Wy kin hjir letter ek fan meitsje dat er troch gjit mei et spul, maar
                # foar eerst stopje wy it hiele programma
                #
                # Dizze útsundering krije wy te sjen ast de Arduino fan sien poart ôf neukst
                print("In IO error jung")
                self.serial_port_available = False
                self.unrecoverable_error = True
                self.last_status = ''
                self.shutdown_flag.set()

            if b'\n' in self.byte_buffer:
                # No sette we de ûntfangen gegevens om nei in formaat dêr't wy wat mei kinne
                lines = self.byte_buffer.decode('utf-8').split('\n')  # Sjuuuh, dan ha je gewoan twaa buffer rigeltsjes

                if lines[-2]:
                    if "a::" in lines[-2]:
                        try:
                            # Yngewikkelds stjit hjir, mar wy bin d'r wer út kaam
                            # As't my fregest hoe't dit wurket, sla ik dy mei de klomp op 'e harses, it wurket!
                            # Wy krije in kaai wer werom, en dat is in tiitkaai, mei djoere wurden, in timestamp
                            # Sa kin wy de antwurden fan de kommandoos dy't wy de Arduino stjoert ha, út in oar hâlde
                            #
                            # De tiitsleutels ha we mei dit script sels nei de Arduino stjoert. En dat jouwt er ûs
                            # wer werom. Se wurre dus net bepaalt troch de Arduino sels
                            timestamp_key = int(lines[-2][3:].split('=')[0])

                            # Opdrachten die't let wer werom kaam binne, opneuke d'r mei
                            # Der wurdt neat mear mei dien. It haadproses, die hjir op wachte,
                            # is al wer drok mei oare saken
                            if round(time.time()) - timestamp_key > self.seconds_to_keep_commands:
                                pass

                            # Hawwe in korrekt antwurd fan dat Arduino apparaat, dan bewarje wy dat foar
                            # it haadproses om út te lêzen
                            self.arduino_answers[timestamp_key] = lines[-2][lines[-2].find('=') + 1:]
                        except TypeError:
                            pass
                    else:
                        # Hjir bewarje wy de oare berjochten fan de Arduino. Hjir hawwe net om frege, mar
                        # it skotsje ferteld ûs mei nocht eefkes hoe't syn dei ferrint
                        self.last_status = lines[-2]

                # Sjoch, wy hawwe in buffer ferdield tot it teken foar in neie regel (\n)
                # Mar dan sit der nog wol wat yn de buffer dat belangryk is foar de bou fan de
                # folgjende regel dat wy yn de folgjende loop wer útlêze.
                self.byte_buffer = bytearray(lines[-1], 'utf-8')

            # Die âlde rommel wurdt net mear brûkt, opneuke mei die bende
            for key in list(self.arduino_answers.keys()):
                if round(time.time()) - key > self.seconds_to_keep_commands:
                    del self.arduino_answers[key]

        # Gewoan in notifikaasje om witten te litten dat it triedsje stoppe is
        print("Is it triedsje al wer afrûn, hast dat sels verneukt, of idder wot mis?")


class ServiceExit(Exception):
    """ Hjir hawwe efkes in eigen útsûndering makke dy't
        wy sels goaie kinne en dêrnei op it goede plak werom fange kinne
        om de triedsjes en it programma sels netsjes ôf te slúten
    """
    pass


# noinspection PyUnusedLocal
def service_shutdown(signal_number, frame):
    """ Funksje allinnig mar om de útsûndering te goaien
        Sinjaal en it raamke dat er noadig hat dêr is de bibliooteek "signal" foar noadig
        Dus boppe oan yn it script stjit "import signal"
        En ien het haadproces (main()), jouwe wy oan welk sinjaal dat'r nei luusterje mat,
        om dêrna dizze funksje oan te roppen

        Op dizze wize mat dat gebirre:
        signal.signal(signal.SIGTERM, service_shutdown)
        signal.signal(signal.SIGINT, service_shutdown)

        Mast mar es opsykje welke sinjalen te belústerjen binne (SIGINT, SIGTERM, SIGQUIT, ...)
        Foar no is dit genôch, omdat it script bedoeld is om ien in terminal te rinnen
    """
    print('Programma is ûnderbrekke, mei it folgjende sinjaal: ' + str(signal_number))
    raise ServiceExit


def main():
    """ It haadproses
        Hjir kin wy it saakje mei draaiende krije
    """

    # Hjir melde wy üs oan aan de sinjalen fan het bestjoeringssysteem
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)

    # Wy matte eerst even in lege wurker oan meitsje
    # Sjoch as er in útsundering krijt foardat ie echt
    # oanmakke wurt, dan soe de code om de útsundering op
    # te fangen it bestean fan dizze wurker net wiete
    # Je witte mar noait fansels. No sa!
    receiver_job = None

    try:
        # No sa! De seriële poart even oan meitsje
        # Dit hat in biblioteek noadig, boppe oan it script
        # stjit: "from serial import *" dus wy ha alle funksjes
        # en variabelen lekker makkelijk tot ûs beskikking fan dizze
        # biblioteek.
        #
        # Net in wiis plan, wist do op it lêst dan noch wêr al die brûkberre
        # funksjes en variabelen wei komme?
        #
        # Better kin wy de biblioteek op dizze manier lade: "import serial"
        ser = Serial(
            port=arduino_port,
            baudrate=arduino_baudrate,
            bytesize=EIGHTBITS,
            parity=PARITY_NONE,
            stopbits=STOPBITS_ONE,
            timeout=0.1,
            xonxoff=0,
            rtscts=1
        )

        # No hawwe der oan de boppekant fan dit moaie stikje programmacode
        # in hurde wurker stean dy't nog neat docht. Wy sille em rúmte jaan
        # om syn wurk te dwaan troch it oanmeitsjen fan in object, it triedsje
        # makket er sels oan, dat hawwe moai regele ien de wurker sels, fienst
        # ek net? Wy matte dizze wurkaholic allinig noch fertelle dat
        # er starte mei, noh ja, en dat sille wy dwaan ek hjir ûnder
        receiver_job = ReceiverJob(ser, round(command_timeout) + 5)
        receiver_job.start()
        flipflop = 0

        # Úteinlik nei al die tarieding, komme wy hjir, dit stikje rint
        # ûneinich troch, tot dat dêr wat mis is, of ôfslúte mat.
        # Hjir komt de aksje dy't wy dwaan wolle
        while True and not receiver_job.unrecoverable_error:
            if receiver_job.last_status == '':
                print('.', end='', flush=True)
                sleep(2)
                continue

            # Efkes sjen wat it sels te sizzen hat
            print()
            print("Status:\t" + receiver_job.last_status)

            # Wy hawwe in tiit noadig, foar ûs tiitkaai
            # Mar ferstjûre it oars nei de Arduino, en wy hâlde
            # dizze tiit efkes tot achter de komma. Sa kin wy tot
            # achter de komma de tiit berekenje dy't it noadig
            # hat om it kommando te stjoeren, te ferwurkjen, en
            # wer werom te krijen.
            command_timestamp = time.time()

            # No sille wy dat saakje efkes omsette sûnder de komma
            # Sa stjûre wy dat nei de Arduino ta, sa dat wy witte
            # as dêr reaksje op is, hokker kommando by hokker reaksje heard
            #
            # Wês aldermachtigst foarsichtig mei dizze kaai, brûk altyd in koeske
            # tusken troch, oars dan hawwe doebele kaai's te ferwurkjen. Ik warskôgje
            # allinig, as it flucher moat, brûk dyn harsens es in kear om in oare kaai
            # út te finen.
            timestamp = round(command_timestamp)

            # Frei om hjir alles te stjoeren, mar sa mat it:
            writing = str(timestamp) + "=13:" + str(flipflop)
            ser.write(bytes(writing, 'utf-8'))

            # Wy wachtsje op antwurt, mar net te lang, wy hawwe oar spul te dwaan, ho is even!
            while timestamp not in receiver_job.arduino_answers.keys() \
                    and (time.time() - command_timestamp) < command_timeout:
                pass

            # Hawwe it werkelijk wer werom? Noh ja, en as't sa is, witte wy dat it
            # kommando slache is
            if timestamp in receiver_job.arduino_answers.keys():
                seconds_it_took = time.time() - command_timestamp

                print(receiver_job.arduino_answers[timestamp])
                print("It kommando naam " + str(round(seconds_it_took, 3)) + " van us tiit")

                sleep(2)

                if flipflop == 0:
                    flipflop = 1
                else:
                    flipflop = 0
            else:
                # En oars, ferrek, der doocht iets net! Miskien hast de ellende oerstjoer makke mei
                # tefolle wurk?
                print("Command " + writing + " failed, timeout of " +
                      str(round(command_timeout, 3)) + " seconds reached")

    except SerialException:
        print("De Arduino is net oansluuten, of dat ding hat in oare poort namme kriegen. " +
              "Mast em even ien in oar USB gotsje stekke! Oars dan mast mie wer in oare " +
              "lokaasje opjaan ien mien programma code. Dizze lokaasje hak no: " + arduino_port)

        # Wy slúte ôf mei in 1, dit jouwt oan het bestjoeringssysteem it sinjaal
        # dat it programma net goed âfslúten is, want ja, d'r is wat mis, ist net sa?
        exit(1)

    except ServiceExit:
        """ Wy hawwe de útsundering kriegen foar ôfslúten
            Wy vertelle it wurker triedsje dat er sien saakjes
            klear meitsje mat, en op te neuken.
            
            Wy matte dan it aparte proses mei it haadproses verbiene, sa
            dat it saakje mei it haadproses tegeare ôfslúte kin.
        """
        if receiver_job:
            receiver_job.shutdown_flag.set()
            receiver_job.join()

    print("Verjit net de skroeve te smarjen!")


if __name__ == '__main__':
    """ Noh ja, dit hoecht net sa, mar tis toch moai dat it sa kin, tinkst net?
    
        Ik bedoel, wat iddat no: "if __name__ == '__main__':" dot sjocht d'r toch net ût?
    """
    main()
