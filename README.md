# blind-controller
Der Blind Controller ist der Regler des Systems BlindControl.
Die Kommunikation zu und von ihm geschieht mittels MQTT.
Mit einem Python Skript werden die Sensordaten des Sensor Moduls empfangen und ausgewertet.
Bei einer Änderung des Jalousie Stands, wird die neue Position an das Aktor Modul gesendet.
Zusätzlich können auch manuelle Änderungswünsche entgegengenommen werden und entsprechend verarbeitet und ausgewertet werden.
