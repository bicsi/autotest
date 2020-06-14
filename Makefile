build:
	g++ -std=c++11 main.cpp -o main
debug:
	g++ -std=c++11 -DTU_DEBUG main.cpp -o main
clean:
	rm main