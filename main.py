#!/usr/bin/python3

""" Boardcomputer fan De Genieter

    Een script om de elektroanika oan te stjoeren op een slimme manier
    Dit script is makke foar de raspberry pi, mar kin op elke pc my python fêst draaie

    Bedoeld om een microcontroller lykas een Arduino oan te stjoeren

    De Arduino hat net alle mooglikheden as een Raspberry om te communiceren my wifi/skermen/bluetooth
    Maar de Raspberry kin dan wer net op sinjaal nivo de apparatuer oan stjoere, zonder
    dat we der wer djoere dingen foar oan skafje matte

    Sa bringe we de ferwurkingskrêft fan de raspberry en de betrouberens en elektryske kracht
    fan een microcontroller as een Arduino by inoar
"""

# Alderwertske seriele kommunikaasje foar python
from serial import *

# We matte altyd in bytsje tiid frij meitsje om in koeske te dwaan
from time import sleep

# Een apart triedsje meitsje we oan om apart fan ûs programma gegevens te krijen fan de Arduino
# Sa hawwe yn dit Python script twa, of meer kin ek natuurlijk, programma's draaien in ien script
# Sa meitsje wy et makkelijker om wat te moois te meitsjen my ûs eigen gerommel yn het main() proses
from threading import Thread, Event

# Hjir kin we de CTRL-C en KILL sinjalen fan et bestjoeringssysteem my harkje
# Sa ha we sels de macht om goed of te slúten en nog krekt wat dinkjes te regelen foar
# dat we de boel âfsluute, as we dan ek mar ofslúte, et bestjoeringssysteem mat yn it gefal
# dat er wat is, lykas een reboot of in geheugen probleem, de macht hâlde om het programma te slûten
import signal

"""Ynstellings dy wy makkelijk even feroarje kinne"""

# Seriële poart wêr dat de Arduino oan hinget
# Disse kin wol es feroarje ast dat ding te snel oppenei yn een USB gotsje stekkest
# Dan krijt er bygelyks wol es de namme /dev/ttyUSB1
arduino_port = "/dev/ttyUSB0"

# De snelhiet fan de kommunikaasje tussen de Arduino en disse computer
# Dit kinst feroarje, et kin nog folle sneller fansels
# Maar disse snelhiet mat geliek weze oan de ynstellings fan de Arduino
# Dus net oanpasse ast et op de Arduino ek net oanpast!
#
# Standert ynstelling foar de meeste seriële apparaten is 9600
# Dus dat hak mar sa litten
#
# De Arduino kin mei een snelhiet fan 115200 oan de skieterij wêze, hoe
# moai dat ek is, dot is tink ik meer om realtime gegevens te sammeljen.
# En dêr broeke we et spul net foar.
#
# Dus 9600 is meer as genôch. En een legere snelhiet is bygelyks minder gefoelich
# foar stoor sinjalen
arduino_baudrate = 9600

# Wy meitsje de stapel commando's dy't wy ontvangen hieden nei een skoftke wer skjin
# Dan bin wy dêr wis fan dat it saakje sien geheugen net op brûkt as wy dit
# programma in skoftsje oan stean litte
command_timeout = 5.0


class ReceiverJob(Thread):
    """ Een wurker wêr dat wy de status en kommando's wer werom mei krije van de Arduino
        Hjir meitsje we yn it haadprogramma (main()) een apart kuierend triedsje fan
    """

    def __init__(self, serial, seconds_to_keep_commands):
        """ Dit is de constructor fan it beestje
            Dit brûkst om disse kloat oan te meitsjen en wêr dûdelijk is wot er noadig is fan jo
            En dot bin de folgjende parameters:

            Parameters:
            serial (Serial):                It "Serial" objekt, ût de pySerial biblioteek (brûk "pip install pyserial")
            seconds_to_keep_commands (int): Hoe lang in sekonden dat we de kommando's ophoopje
        """
        Thread.__init__(self)

        self.serial = serial
        self.byte_buffer = bytearray()
        self.serial_port_available = True
        self.unrecoverable_error = False
        self.seconds_to_keep_commands = seconds_to_keep_commands

        # Wy hawwe spitigernôch gjin iepenbare en privee mooglikheden in python
        # Ik haw disse fariabelen mar even apart setten mei dit kommentaar
        # Disse binne bedoeld om ût te lêzen troch it haadtriedsje (main())
        # Hjir kin we dus wat mei, de fariabelen hjir boppe rêd it beestje hjir sels mei
        self.arduino_answers = {}
        self.last_status = ''

        # Disse is net belangryk foar wat wy noadig binne,
        # Mar ik set it hjir even del om dat disse eins ek iepenbaar is
        # Disse brûke we yn it gefal dat we afslûte wolle of dêr is een oare reden om
        # dit triedsje te stopjen
        # Een apart triedsje kin ommers gjin sinjalen ontvangen fan het bestjoeringssysteem
        # Disse sinjalen krijt het haadproses (main()), mar it haadproses kin efter dat it sa'n
        # sinjaal krijt, dit flagje oanpasse, sa dat it triedsje wiet dat er ofslúte mat, sa
        # kin er sien spultsje nog even ôfmeitsje, we brûke dêr dit kommando foar yn het
        # haadproses (main()):
        #
        # hoest_disse_klasse_ek_mar_oan_makke_hiedest.shutdown_flag.set()
        self.shutdown_flag = Event()

    def run(self):
        # We stopje net earder dan dat wy de oarder krije om de geest te jaan
        while not self.shutdown_flag.is_set():
            try:
                # We stopje ûs bufferke vol mei all wat et bestjoeringssysteem foar
                # ûs sammelje hat, fan de seriële keppeling mei de Arduino
                self.byte_buffer.extend(self.serial.read(self.serial.inWaiting()))

                # Even sliepe, oars hat et processorke gjin tiit meer foar oare dingen
                sleep(0.01)
            except SerialException:
                # Hjir gjit et mis mei de keppeling, kin komme troch dast er mei dien
                # brieke klauwen oan sist, mar kin ek wêze dat een oar programma ûs poart
                # stellen hat
                #
                # We soargje d'r hjir foar dat we rinnende bliuwe en besykje de keppeling
                # werom te heljen
                self.serial_port_available = False

                # We witte net hoe lang dat d'r fjot wêst is, we meitsje de buffers skjin
                # Dat sil fêst net meer klopje, tinkst al?
                self.arduino_answers = {}
                self.last_status = ''
                self.byte_buffer = bytearray()

                # No kin we de keppeling slúte
                self.serial.close()

                # En wachtsje we wer tot er d'r wer is
                while not self.serial_port_available:
                    try:
                        for x in range(10, 0, -1):
                            sleep(1)
                            print('\r We starte de seriële bende wer oer san ' + str(x) + ' seconden'),

                        # We iepenje et saakje wer, en at d'r nog net beskikber is, dan
                        # goait er een útsundering (SerialException), en krije we ús printsje
                        # dat er d'r wer is net te sjen
                        self.serial.open()
                        print('Seriële poarte idder, we gjin wer troch ...')

                        self.serial_port_available = True
                    except SerialException:
                        print("Seriële poart idder nog steeds net boeke ....")

                continue
            except OSError:
                # Disse útsundering hie ik fan ferwachte dat er fangt wêze soe troch
                # de SerialException, docht er net, dus fange wy et sels mar op
                # We kin hjir letter ek fan meitsje dat er troch gjit mei et spul, maar
                # foar eerst stopje we it hiele programma
                #
                # Disse útsundering krije wy te sjen ast de Arduino fan sien poart ôf neukst
                print("Een IO error jung")
                self.serial_port_available = False
                self.unrecoverable_error = True
                self.last_status = ''
                self.shutdown_flag.set()

            if b'\n' in self.byte_buffer:
                # No sette we de ûntfangen gegevens om nei een formaat dêr't wy wat mei kinne
                lines = self.byte_buffer.decode('utf-8').split('\n')  # Sjuuuh, dan ha je gewoan twaa buffer rigeltsjes

                if lines[-2]:
                    if "a::" in lines[-2]:
                        try:
                            # Yngewikkelds stjit hjir, mar wy bin d'r wer út kaam
                            # As't my fregest hoe't dit wurket, sla ik dy mei de klomp op 'e harses, it wurket!
                            # We krije een kaai wer werom, en dat is in tiitkaai, mei djoere wurden, in timestamp
                            # Sa kin antwurden fan de Arduino fan we de kommando's dat wy stjoere, út in oar hâlde
                            timestamp_key = int(lines[-2][3:].split('=')[0])

                            # Opdrachten die't let wer werom kaam kinne, opneuke
                            # Der wurdt neat mear mei dien. It haadproses, die hjir op wachte,
                            # is al wer drok mei saken
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

                # Sjoch, wy hawwe een buffer ferdield tot it teken foar in neie regel (\n)
                # Mar dan sit der nog wol wat yn de buffer dat belangryk is foar de bou fan de
                # folgjende line dat wy yn de folgjende loop wer útlêze.
                self.byte_buffer = bytearray(lines[-1], 'utf-8')

            # Die âlde rommel wurdt net mear brûkt, opneuke mei die bende
            for key in list(self.arduino_answers.keys()):
                if round(time.time()) - key > self.seconds_to_keep_commands:
                    del self.arduino_answers[key]

        # Gewoan een notifikaasje om witten te litten dat it triedsje stoppe is
        print("Is it triedsje al wer afrûn, hast dat sels verneukt, of idder wot mis?")


class ServiceExit(Exception):
    """ Hjir hawwe even een eigen útsûndering makke dy't
        wy sels goaie kinne en dêrnei op it goede plak werom fange kinne
        om de triedsjes en it programma sels netsjes ôf te slúten
    """
    pass


# noinspection PyUnusedLocal
def service_shutdown(signal_number, frame):
    """ Funksje allinnig mar om de útsûndering te goaien
        Sinjaal en it raamke dat er noadig hat dêr is de bibliooteek "signal" foar noadig
        Dus boppe oan yn it script stjit "import signal"
        En ien het haadproces (main()), jouwe wy oan welk signaal dat'r nei luusterje mat,
        om dêrna dizze funksje oan te roppen

        Op dizze wize mat dat gebirre:
        signal.signal(signal.SIGTERM, service_shutdown)
        signal.signal(signal.SIGINT, service_shutdown)

        Mast mar es opsykje welke sinjalen te belústerjen binne (SIGINT, SIGTERM, SIGQUIT, ...)
        Foar no is dit genôch, omdat it script bedoeld is om ien in terminal te starten
    """
    print('Programma is ûnderbrekke, mei it folgjende sinjaal: ' + str(signal_number))
    raise ServiceExit


def main():
    signal.signal(signal.SIGTERM, service_shutdown)
    signal.signal(signal.SIGINT, service_shutdown)

    receiver_job = None

    try:
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

        receiver_job = ReceiverJob(ser, round(command_timeout) + 5)
        receiver_job.start()
        flipflop = 0

        while True and not receiver_job.unrecoverable_error:
            if receiver_job.last_status == '':
                print('.', end='', flush=True)
                sleep(2)
                continue

            print()
            print("Status:\t" + receiver_job.last_status)

            command_timestamp = time.time()

            timestamp = round(command_timestamp)
            writing = str(timestamp) + "=13:" + str(flipflop)
            ser.write(bytes(writing, 'utf-8'))

            while timestamp not in receiver_job.arduino_answers.keys() \
                    and (time.time() - command_timestamp) < command_timeout:
                pass

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
                print("Command " + writing + " failed, timeout of " +
                      str(round(command_timeout, 3)) + " seconds reached")

                for key in receiver_job.arduino_answers.keys():
                    print(key)

    except SerialException:
        print("De Arduino is net oansluuten, of dat ding hat een oare poort namme kriegen. " +
              "Mast em even ien een oar USB gotsje stekke! Oars dan mast mie wer een oare " +
              "lokaasje opjaan ien mien programma code. Disse lokaasje hak no: " + arduino_port)
        exit(1)

    except ServiceExit:
        if receiver_job:
            receiver_job.shutdown_flag.set()
            receiver_job.join()

    print("Verjit net de skroeve te smarjen!")


if __name__ == '__main__':
    main()
