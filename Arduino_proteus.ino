#include <TimerOne.h>
#include <PID_v1.h>

const int out_voltage_pin_system = A3;
const int pwm_pin = 9;

double expected_output_voltage = 13.0; 

double Setpoint, Input, Output;
double current_target = 0.0;


double Kp = 3.57, Ki = 143.0, Kd = 0.0; 

int hardware_duty_cycle;
PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

unsigned long lastPrintTime = 0;

void setup() {
  pinMode(pwm_pin, OUTPUT);
  

  Timer1.initialize(100);
  Timer1.pwm(pwm_pin, 0); 
  
  delay(200);
  Serial.begin(115200);

  Input = read_out_voltage();
  Setpoint = 0.0; 
  Output = 0;     
  
  myPID.SetOutputLimits(0, 1023); 
  myPID.SetSampleTime(10);        
  myPID.SetMode(AUTOMATIC); 
}

void loop() {

  if (current_target < expected_output_voltage) {
    current_target += 0.02; 
    Setpoint = current_target;
  }

  Input = read_out_voltage();
  
  if (myPID.Compute()) {
    apply_pwm_control();
  }

  if (millis() - lastPrintTime >= 100) {
    Serial.print("Target: "); Serial.print(Setpoint);
    Serial.print("V | Real: "); Serial.print(Input);
    Serial.print("V | PWM Effort: "); Serial.println(Output);
    lastPrintTime = millis();
  }
}

double read_out_voltage() {
  int raw_adc = analogRead(out_voltage_pin_system);
  return (raw_adc * 50.5357) / 1023.0;
}

void apply_pwm_control() {
  hardware_duty_cycle = (int)Output;
  
  hardware_duty_cycle = constrain(hardware_duty_cycle, 0, 1018);
  Timer1.pwm(pwm_pin, hardware_duty_cycle);
}
