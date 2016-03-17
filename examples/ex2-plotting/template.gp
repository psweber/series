
dataFile='dataFiles/OPT_DATAFILE'
caseName='OPT__CASENAME'
outFile='OPT__SERIESNAME-'.caseName.'.png'

set terminal png
set output outFile

set xlabel "Position"
set ylabel "Intensity"
set title "Quantity XY vs. Position"
set grid

plot  \
	'< sort '.dataFile.'' \
	using 1:3 \
	title "Case \"".caseName."\""

set output
