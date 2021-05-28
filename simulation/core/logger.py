import logging
from datetime import datetime

prefix = datetime.today().isoformat(sep=' ')

logger = logging.getLogger('asa')
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("results/" + prefix + "--ASA.log")
formatter = logging.Formatter('[%(levelname)s] : %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

latency_logger = logging.getLogger('latency')
latency_logger.setLevel(logging.INFO)

f = logging.FileHandler("results/" + prefix + "--Latency.log")
frmt = logging.Formatter('[%(levelname)s] : %(message)s')
f.setFormatter(frmt)

latency_logger.addHandler(f)

receive_logger = logging.getLogger('receive')
receive_logger.setLevel(logging.INFO)

fr = logging.FileHandler("results/" + prefix + "--Throughput.log")
frmtr = logging.Formatter('%(message)s')
fr.setFormatter(frmtr)

receive_logger.addHandler(fr)

LogName = prefix + "--Latency.log"
